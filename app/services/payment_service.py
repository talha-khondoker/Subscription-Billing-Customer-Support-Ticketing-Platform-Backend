# ----------------------------------------------------------------------
# app/services/payment_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - attempt_payment(db, invoice)  -> creates payment + attempt 1 via mock_gateway
#   - pay_invoice(db, customer, invoice_id)
#   - list_payments(db, user, filters, page)
#   - get_attempts(db, payment_id)
#   - on success: invoice paid; on failure: store reason and ask retry_service for next time

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import InvoiceStatus, PaymentStatus, Role
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentAttempt
from app.services.mock_gateway import charge
from app.utils.dates import utcnow


def attempt_payment(db: Session, invoice: Invoice) -> Payment:
    """Create a payment attempt for an invoice."""

    if invoice.customer is None:
        raise HTTPException(status_code=400, detail="Invoice has no customer")
    if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.REFUNDED, InvoiceStatus.VOID):
        raise HTTPException(
            status_code=409,
            detail=f"Invoice cannot be paid while it is {invoice.status.value}",
        )

    payment = db.scalar(
        select(Payment).where(Payment.invoice_id == invoice.id).order_by(Payment.id.desc())
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
        payment.amount = invoice.total
        payment.status = PaymentStatus.PENDING

    result = charge(payment.amount, invoice.customer)
    attempt_number = len(payment.attempts) + 1
    attempt = PaymentAttempt(
        payment_id=payment.id,
        invoice_id=invoice.id,
        attempt_number=attempt_number,
        status="succeeded" if result["success"] else "failed",
        gateway_response=result,
    )
    db.add(attempt)

    if result["success"]:
        payment.status = PaymentStatus.SUCCEEDED
        payment.gateway_reference = result["gateway_reference"]
        payment.failure_reason = None
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = utcnow()
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = result["message"]
        invoice.status = InvoiceStatus.FAILED
        from app.services.retry_service import schedule_next_retry
        db.flush()
        schedule_next_retry(db, payment, attempt)

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
