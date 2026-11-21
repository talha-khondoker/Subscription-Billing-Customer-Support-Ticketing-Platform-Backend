# ----------------------------------------------------------------------
# app/routers/payments.py
# Owner:   Member 4
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /invoices/{id}/pay [CU]  pay through the mock gateway
#   - GET  /payments/me [CU]
#   - GET  /payments [OA, AG]
#   - GET  /payments/{id}/attempts [CU, OA, AG]
#   - POST /payments/{id}/refund [OA]
#   - GET  /refunds [OA]
#   - PUT  /gateway/mock-config [OA]  set mock result mode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_customer, current_org_admin, current_staff, require_roles
from app.core.enums import PaymentStatus, Role
from app.models.payment import Payment, Refund
from app.models.user import User
from app.schemas.common import Page
from app.schemas.payment import MockGatewayConfig, PaymentAttemptOut, PaymentOut, RefundCreate, RefundOut
from app.services import mock_gateway, payment_service, refund_service

router = APIRouter(tags=["payments"])


def _payment_page(db: Session, user: User, page: int, page_size: int, status: PaymentStatus | None):
    items = payment_service.list_payments(db, user, status, page, page_size)
    count = select(func.count()).select_from(Payment)
    if user.role == Role.CUSTOMER:
        if user.customer_profile is None:
            return Page[PaymentOut](items=[], total=0, page=page, page_size=page_size)
        count = count.where(Payment.customer_id == user.customer_profile.id)
    else:
        count = count.where(Payment.organization_id == user.organization_id)
    if status is not None:
        count = count.where(Payment.status == status)
    return Page[PaymentOut](items=items, total=db.scalar(count) or 0, page=page, page_size=page_size)


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentOut)
def pay_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(current_customer)):
    if user.customer_profile is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return payment_service.pay_invoice(db, user.customer_profile, invoice_id)


@router.get("/payments/me", response_model=Page[PaymentOut])
def my_payments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    status: PaymentStatus | None = None, db: Session = Depends(get_db),
    user: User = Depends(current_customer),
):
    return _payment_page(db, user, page, page_size, status)


@router.get("/payments", response_model=Page[PaymentOut])
def list_payments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    status: PaymentStatus | None = None, db: Session = Depends(get_db),
    user: User = Depends(current_staff),
):
    return _payment_page(db, user, page, page_size, status)


@router.get("/payments/{payment_id}/attempts", response_model=list[PaymentAttemptOut])
def get_payment_attempts(
    payment_id: int, db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.CUSTOMER, Role.ORG_ADMIN, Role.AGENT)),
):
    query = select(Payment).where(Payment.id == payment_id)
    if user.role == Role.CUSTOMER:
        if user.customer_profile is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        query = query.where(Payment.customer_id == user.customer_profile.id)
    else:
        query = query.where(Payment.organization_id == user.organization_id)
    if db.scalar(query) is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment_service.get_attempts(db, payment_id)


@router.post("/payments/{payment_id}/refund", response_model=RefundOut)
def refund_payment(
    payment_id: int, data: RefundCreate, db: Session = Depends(get_db),
    user: User = Depends(current_org_admin),
):
    payment = db.scalar(select(Payment).where(
        Payment.id == payment_id, Payment.organization_id == user.organization_id,
    ))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return refund_service.create_refund(db, user, payment, data.amount, data.reason)


@router.get("/refunds", response_model=Page[RefundOut])
def list_refunds(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(current_org_admin),
):
    items = refund_service.list_refunds(db, user.organization_id, page, page_size)
    total = db.scalar(select(func.count()).select_from(Refund).where(
        Refund.organization_id == user.organization_id,
    )) or 0
    return Page[RefundOut](items=items, total=total, page=page, page_size=page_size)


@router.put("/gateway/mock-config")
def configure_mock_gateway(data: MockGatewayConfig, _user: User = Depends(current_org_admin)):
    return {"mode": mock_gateway.set_mode(data.mode)}
