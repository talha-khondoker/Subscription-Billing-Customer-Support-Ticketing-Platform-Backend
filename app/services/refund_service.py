# ----------------------------------------------------------------------
# app/services/refund_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_refund(db, admin, payment, amount, reason)  -> cannot exceed paid amount minus earlier refunds
#   - full refund marks invoice and payment refunded
#   - list_refunds(db, org_id, page)
#   - always write an audit log

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import InvoiceStatus, PaymentStatus, RefundStatus
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.models.payment import Payment, Refund
from app.models.user import User


def create_refund(
    db: Session,
    admin: User,
    payment: Payment,
    amount: Decimal,
    reason: str | None = None,
) -> Refund:
    # Validate the refund before changing any payment or invoice.
    payment = db.scalar(select(Payment).where(Payment.id == payment.id).with_for_update()) or payment
    if admin.organization_id != payment.organization_id:
        raise HTTPException(status_code=404, detail="Payment not found")
    old_status = payment.status
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Refund must be greater than zero")
    if payment.status not in (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED):
        raise HTTPException(status_code=409, detail="Only successful payments can be refunded")

    refunded_amount = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), Decimal("0.00"))).where(
            Refund.payment_id == payment.id,
            Refund.status == RefundStatus.COMPLETED,
        )
    ) or Decimal("0.00")
    if amount > payment.amount - refunded_amount:
        raise HTTPException(
            status_code=409,
            detail="Refund amount exceeds remaining refundable amount",
        )

    refund = Refund(
        organization_id=payment.organization_id,
        payment_id=payment.id,
        invoice_id=payment.invoice_id,
        amount=amount,
        reason=reason,
        issued_by=admin.id,
        status=RefundStatus.COMPLETED,
    )
    db.add(refund)
    db.flush()

    if amount == payment.amount - refunded_amount:
        payment.status = PaymentStatus.REFUNDED
        invoice = payment.invoice or db.get(Invoice, payment.invoice_id)
        if invoice is not None:
            invoice.status = InvoiceStatus.REFUNDED

    db.add(
        AuditLog(
            organization_id=payment.organization_id,
            actor_id=admin.id,
            action="payment.refund",
            entity_type="refund",
            entity_id=refund.id,
            old_values={"payment_status": old_status.value},
            new_values={"amount": str(amount), "reason": reason},
        )
    )
    db.commit()
    db.refresh(refund)
    return refund


def list_refunds(
    db: Session,
    org_id: int,
    page: int = 1,
    page_size: int = 20,
) -> list[Refund]:
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Page and page size must be positive")
    query = (
        select(Refund)
        .where(Refund.organization_id == org_id)
        .order_by(Refund.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(query).all())
