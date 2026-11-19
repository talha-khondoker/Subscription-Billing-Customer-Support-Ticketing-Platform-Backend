# ----------------------------------------------------------------------
# tests/test_retry_schedule.py
# Owner:   Member 4
# Purpose: Retry rules.
# ----------------------------------------------------------------------
# TODO:
#   - schedule 1/3/5 days
#   - past_due after max attempts
#   - success stops retries

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models
from app.core.database import Base
from app.core.enums import (
    AttemptStatus,
    BillingPeriod,
    InvoiceStatus,
    PaymentStatus,
    Role,
    SubscriptionStatus,
)
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.models.payment import Payment, PaymentAttempt
from app.services import retry_service
from app.services.retry_service import run_due_retries, schedule_next_retry
from app.utils.dates import utcnow


@pytest.fixture
def db():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_retry_data(db: Session) -> tuple[Payment, Invoice, Subscription]:
    """Create one organization, customer, subscription, invoice, and failed payment."""
    organization = Organization(name=f"Retry Org {utcnow().timestamp()}")
    db.add(organization)
    db.flush()

    customer_user = User(
        organization_id=organization.id,
        email=f"customer-{utcnow().timestamp()}@test.local",
        password_hash="test",
        full_name="Retry Customer",
        role=Role.CUSTOMER,
    )
    admin = User(
        organization_id=organization.id,
        email=f"admin-{utcnow().timestamp()}@test.local",
        password_hash="test",
        full_name="Retry Admin",
        role=Role.ORG_ADMIN,
    )
    db.add_all([customer_user, admin])
    db.flush()

    customer = Customer(
        organization_id=organization.id,
        user_id=customer_user.id,
    )
    plan = Plan(
        organization_id=organization.id,
        name=f"Retry Plan {utcnow().timestamp()}",
        price=Decimal("10.00"),
        billing_period=BillingPeriod.MONTHLY,
    )
    db.add_all([customer, plan])
    db.flush()

    now = utcnow()
    subscription = Subscription(
        organization_id=organization.id,
        customer_id=customer.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        next_billing_date=now,
    )
    db.add(subscription)
    db.flush()

    invoice = Invoice(
        organization_id=organization.id,
        customer_id=customer.id,
        subscription_id=subscription.id,
        invoice_number=f"INV-{utcnow().timestamp()}",
        total=Decimal("10.00"),
    )
    db.add(invoice)
    db.flush()

    payment = Payment(
        organization_id=organization.id,
        invoice_id=invoice.id,
        customer_id=customer.id,
        amount=Decimal("10.00"),
        status=PaymentStatus.FAILED,
    )
    db.add(payment)
    db.flush()
    db.commit()
    return payment, invoice, subscription


@pytest.mark.parametrize(
    ("attempt_number", "expected_days"),
    [(1, 1), (2, 3)],
)
def test_retry_schedule_days(attempt_number, expected_days):
    """Attempt 1 waits 1 day and attempt 2 waits 3 days."""
    retry_service.settings.RETRY_SCHEDULE_DAYS = [1, 3, 5]
    retry_service.settings.MAX_RETRY_ATTEMPTS = 3

    attempt = PaymentAttempt(
        payment_id=1,
        invoice_id=1,
        attempt_number=attempt_number,
        status=AttemptStatus.FAILED,
    )
    payment = Payment(attempts=[attempt])
    before = utcnow()

    scheduled = schedule_next_retry(None, payment, attempt)

    assert scheduled is not None
    assert scheduled.next_retry_at is not None
    expected = before + timedelta(days=expected_days)
    assert abs((scheduled.next_retry_at - expected).total_seconds()) < 2


def test_maximum_attempt_has_no_retry():
    """The third attempt reaches the maximum limit and has no next retry date."""
    retry_service.settings.RETRY_SCHEDULE_DAYS = [1, 3, 5]
    retry_service.settings.MAX_RETRY_ATTEMPTS = 3
    attempt = PaymentAttempt(
        payment_id=1,
        invoice_id=1,
        attempt_number=3,
        status=AttemptStatus.FAILED,
    )
    payment = Payment(attempts=[attempt])

    scheduled = schedule_next_retry(None, payment, attempt)

    assert scheduled is attempt
    assert scheduled.next_retry_at is None


def test_successful_retry_stops_future_retries(db, monkeypatch):
    """A successful retry marks the payment paid and removes the retry date."""
    payment, invoice, _ = make_retry_data(db)
    previous = PaymentAttempt(
        payment_id=payment.id,
        invoice_id=invoice.id,
        attempt_number=1,
        status=AttemptStatus.FAILED,
        next_retry_at=utcnow() - timedelta(minutes=1),
    )
    db.add(previous)
    db.commit()
    db.refresh(payment)

    monkeypatch.setattr(
        retry_service,
        "charge",
        lambda amount, customer: {
            "success": True,
            "gateway_reference": "mock_success",
            "message": "Payment approved",
        },
    )

    retried = run_due_retries(db)

    assert retried == [payment]
    assert payment.status == PaymentStatus.SUCCEEDED
    assert invoice.status == InvoiceStatus.PAID
    assert len(payment.attempts) == 2
    assert payment.attempts[-1].next_retry_at is None


def test_max_attempts_marks_subscription_past_due(db, monkeypatch):
    """The third failed retry marks the linked subscription past due."""
    retry_service.settings.MAX_RETRY_ATTEMPTS = 3
    payment, invoice, subscription = make_retry_data(db)
    previous = PaymentAttempt(
        payment_id=payment.id,
        invoice_id=invoice.id,
        attempt_number=2,
        status=AttemptStatus.FAILED,
        next_retry_at=utcnow() - timedelta(minutes=1),
    )
    db.add(previous)
    db.commit()
    db.refresh(payment)

    monkeypatch.setattr(
        retry_service,
        "charge",
        lambda amount, customer: {
            "success": False,
            "gateway_reference": None,
            "message": "Payment declined",
        },
    )

    retried = run_due_retries(db)

    assert retried == [payment]
    assert len(payment.attempts) == 2
    assert payment.attempts[-1].attempt_number == 3
    assert payment.attempts[-1].next_retry_at is None
    assert subscription.status == SubscriptionStatus.PAST_DUE
