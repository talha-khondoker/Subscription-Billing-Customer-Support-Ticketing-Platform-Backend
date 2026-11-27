# ----------------------------------------------------------------------
# app/services/payment_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import AttemptStatus, InvoiceStatus, NotificationType, PaymentStatus, Role, SubscriptionStatus
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentAttempt
from app.models.subscription import Subscription
from app.services import notification_service
from app.services.mock_gateway import charge
from app.utils.dates import utcnow


def attempt_payment(db: Session, invoice: Invoice) -> Payment:
    """Create a payment attempt for an invoice."""

    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice.id).with_for_update()) or invoice

    if invoice.customer is None:
        raise HTTPException(status_code=400, detail="Invoice has no customer")
    if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.REFUNDED, InvoiceStatus.VOID):
        raise HTTPException(
            status_code=409,
            detail=f"Invoice cannot be paid while it is {invoice.status.value}",
        )

    if invoice.total <= 0:
        raise HTTPException(status_code=400, detail="There is nothing to pay on this invoice")

    payment = db.scalar(
        select(Payment).where(Payment.invoice_id == invoice.id).with_for_update()
    )
    if payment is None:
        payment = Payment(
            organization_id=invoice.organization_id,
            invoice_id=invoice.id,
            customer_id=invoice.customer.id,
            amount=invoice.total,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.flush()
    else:
        if payment.status == PaymentStatus.SUCCEEDED:
            raise HTTPException(status_code=409, detail="Payment has already succeeded")
        if len(payment.attempts) >= settings.MAX_RETRY_ATTEMPTS:
            raise HTTPException(status_code=409, detail="Maximum payment attempts reached")
        payment.amount = invoice.total
        payment.status = PaymentStatus.PENDING

    result = charge(payment.amount, invoice.customer)
    attempt_number = len(payment.attempts) + 1
    attempt = PaymentAttempt(
        payment_id=payment.id,
        invoice_id=invoice.id,
        attempt_number=attempt_number,
        status=AttemptStatus.SUCCEEDED if result["success"] else AttemptStatus.FAILED,
        gateway_response=result,
    )
    db.add(attempt)

    if result["success"]:
        payment.status = PaymentStatus.SUCCEEDED
        payment.gateway_reference = result["gateway_reference"]
        payment.failure_reason = None
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = utcnow()
        if invoice.subscription_id is not None:  # a successful payment brings a past_due subscription back
            subscription = db.get(Subscription, invoice.subscription_id)
            if subscription is not None and subscription.status == SubscriptionStatus.PAST_DUE:
                subscription.status = SubscriptionStatus.ACTIVE
        notification_service.notify(
            db, invoice.customer.user_id, "Payment received",
            f"Payment for invoice {invoice.invoice_number} succeeded.",
            NotificationType.PAYMENT, organization_id=invoice.organization_id,
        )
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = result["message"]
        invoice.status = InvoiceStatus.FAILED
        from app.services.retry_service import schedule_next_retry
        db.flush()
        schedule_next_retry(db, payment, attempt)
        notification_service.notify(
            db, invoice.customer.user_id, "Payment failed",
            f"We could not charge invoice {invoice.invoice_number}. We will retry automatically.",
            NotificationType.PAYMENT, organization_id=invoice.organization_id,
        )

    db.commit()
    db.refresh(payment)
    return payment


def pay_invoice(db: Session, customer: Customer, invoice_id: int) -> Payment:
    # Check the customer first so another customer's invoice cannot be paid.
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.customer_id == customer.id,
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found for this customer")
    return attempt_payment(db, invoice)


def list_payments(
    db: Session,
    user: Any,
    status: Optional[PaymentStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Payment]:
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive")

    query = select(Payment)
    if user.role == Role.CUSTOMER:
        if user.customer_profile is None:
            return []
        query = query.where(Payment.customer_id == user.customer_profile.id)
    else:
        if user.organization_id is None:
            raise HTTPException(status_code=403, detail="User has no organization")
        query = query.where(Payment.organization_id == user.organization_id)

    if status is not None:
        query = query.where(Payment.status == status)
    query = query.order_by(Payment.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(query).all())


def get_attempts(db: Session, payment_id: int) -> list[PaymentAttempt]:
    query = select(PaymentAttempt).where(
        PaymentAttempt.payment_id == payment_id
    ).order_by(PaymentAttempt.attempt_number)
    return list(db.scalars(query).all())
