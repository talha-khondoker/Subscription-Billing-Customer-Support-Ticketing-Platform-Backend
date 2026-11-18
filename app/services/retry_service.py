# ----------------------------------------------------------------------
# app/services/retry_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - schedule_next_retry(db, payment)  -> uses RETRY_SCHEDULE_DAYS
#   - run_due_retries(db)  -> retry payments whose next_retry_at has passed
#   - after MAX_RETRY_ATTEMPTS failures: subscription past_due + notify admin

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    AttemptStatus,
    InvoiceStatus,
    NotificationType,
    PaymentStatus,
    Role,
    SubscriptionStatus,
)
from app.models.notification import Notification
from app.models.payment import Payment, PaymentAttempt
from app.models.subscription import Subscription
from app.models.user import User
from app.services.mock_gateway import charge
from app.utils.dates import utcnow


def schedule_next_retry(
    db: Session,
    payment: Payment,
    attempt: PaymentAttempt | None = None,
) -> PaymentAttempt | None:
    # Find the latest failed attempt if one was not supplied.
    if attempt is None:
        attempt = max(payment.attempts, key=lambda item: item.attempt_number, default=None)
    if attempt is None or attempt.status != AttemptStatus.FAILED:
        return attempt
    if attempt.attempt_number >= settings.MAX_RETRY_ATTEMPTS:
        return attempt
    if not settings.RETRY_SCHEDULE_DAYS:
        raise HTTPException(status_code=500, detail="Retry schedule is empty")

    position = min(attempt.attempt_number - 1, len(settings.RETRY_SCHEDULE_DAYS) - 1)
    attempt.next_retry_at = utcnow() + timedelta(days=settings.RETRY_SCHEDULE_DAYS[position])
    return attempt


def run_due_retries(db: Session) -> list[Payment]:
    """Retry failed payments whose retry date has arrived."""

    payments = db.scalars(
        select(Payment).where(Payment.status == PaymentStatus.FAILED)
    ).unique().all()
    retried = []

    for payment in payments:
        previous = max(payment.attempts, key=lambda item: item.attempt_number, default=None)
        if previous is None or previous.next_retry_at is None:
            continue
        if previous.next_retry_at > utcnow():
            continue
        if payment.invoice is None or payment.customer is None:
            raise HTTPException(
                status_code=500,
                detail=f"Payment {payment.id} is missing invoice or customer",
            )

        result = charge(payment.amount, payment.customer)
        attempt = PaymentAttempt(
            payment_id=payment.id,
            invoice_id=payment.invoice.id,
            attempt_number=previous.attempt_number + 1,
            status="succeeded" if result["success"] else "failed",
            gateway_response=result,
        )
        db.add(attempt)

        if result["success"]:
            payment.status = PaymentStatus.SUCCEEDED
            payment.gateway_reference = result["gateway_reference"]
            payment.failure_reason = None
            payment.invoice.status = InvoiceStatus.PAID
            payment.invoice.paid_at = utcnow()
            previous.next_retry_at = None
        else:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = result["message"]
            payment.invoice.status = InvoiceStatus.FAILED
            db.flush()
            schedule_next_retry(db, payment, attempt)

            if attempt.attempt_number >= settings.MAX_RETRY_ATTEMPTS:
                if payment.invoice.subscription_id is not None:
                    subscription = db.get(Subscription, payment.invoice.subscription_id)
                    if subscription is not None:
                        subscription.status = SubscriptionStatus.PAST_DUE
                admins = db.scalars(
                    select(User).where(
                        User.organization_id == payment.organization_id,
                        User.role == Role.ORG_ADMIN,
                        User.is_active.is_(True),
                    )
                ).all()
                for admin in admins:
                    db.add(
                        Notification(
                            organization_id=payment.organization_id,
                            user_id=admin.id,
                            title="Payment requires attention",
                            message=f"Payment {payment.id} needs attention.",
                            type=NotificationType.PAYMENT,
                        )
                    )
        retried.append(payment)

    if retried:
        db.commit()
        for payment in retried:
            db.refresh(payment)
    return retried
