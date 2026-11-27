
# ----------------------------------------------------------------------
# app/routers/invoices.py
# Owner: Member 3
# Purpose: HTTP layer only: validate input, check role, call a service,
#          return a schema. No business rules.
# ----------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.enums import Role, InvoiceStatus
from app.schemas.invoice import (
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceFilter,
)
from app.services import invoice_service


router = APIRouter(tags=["Invoices"])


# ----------------------------------------------------------------------
# GET /invoices/me
# Customer can see their own invoices.
# ----------------------------------------------------------------------

@router.get(
    "/invoices/me",
    response_model=InvoiceListResponse,
)
def get_my_invoices(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(Role.CUSTOMER)),
    status: Optional[InvoiceStatus] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    filters = InvoiceFilter(
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    return invoice_service.list_invoices(
        db=db,
        user=current_user,
        filters=filters,
    )


# ----------------------------------------------------------------------
# GET /invoices
# Organization Admin and Agent can see invoices.
# Supports customer, status and date filters.
# ----------------------------------------------------------------------

@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
)
def get_invoices(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(Role.ORG_ADMIN, Role.AGENT)
    ),
    customer_id: Optional[int] = Query(default=None, gt=0),
    status: Optional[InvoiceStatus] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    filters = InvoiceFilter(
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    return invoice_service.list_invoices(
        db=db,
        user=current_user,
        filters=filters,
    )


# ----------------------------------------------------------------------
# GET /invoices/{invoice_id}
# Customer, Organization Admin and Agent can view an invoice.
# ----------------------------------------------------------------------

@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
)
def get_invoice_details(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            Role.CUSTOMER,
            Role.ORG_ADMIN,
            Role.AGENT,
        )
    ),
):
    return invoice_service.get_invoice(
        db=db,
        user=current_user,
        invoice_id=invoice_id,
    )
