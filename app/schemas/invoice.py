
# ----------------------------------------------------------------------
# app/schemas/invoice.py
# Owner: Member 3
# Purpose: Pydantic schemas for invoice request and response validation.
# ----------------------------------------------------------------------
# Notes:
#   - Response schemas use ORM attributes.
#   - Money values use Decimal.
#   - Datetimes are naive UTC.
#   - Invoice items may contain negative amounts.
#
# TODO:
#   - InvoiceItemResponse
#   - InvoiceSummary
#   - InvoiceResponse
#   - InvoiceListResponse
#   - InvoiceFilter
# ----------------------------------------------------------------------

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import InvoiceItemType, InvoiceStatus


# ----------------------------------------------------------------------
# Invoice Item Response Schema
# ----------------------------------------------------------------------

class InvoiceItemResponse(BaseModel):

    id: int
    invoice_id: int

    item_type: InvoiceItemType

    description: str

    quantity: int

    unit_amount: Decimal

    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------
# Invoice Summary Schema
# Used for invoice listing
# ----------------------------------------------------------------------

class InvoiceSummary(BaseModel):

    id: int

    organization_id: int

    customer_id: int

    subscription_id: Optional[int] = None

    invoice_number: str

    period_start: Optional[datetime] = None

    period_end: Optional[datetime] = None

    subtotal: Decimal

    discount_amount: Decimal

    tax_amount: Decimal

    total: Decimal

    status: InvoiceStatus

    due_date: Optional[datetime] = None

    issued_at: datetime

    paid_at: Optional[datetime] = None

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------
# Invoice Response Schema
# Used for single invoice details
# ----------------------------------------------------------------------

class InvoiceResponse(InvoiceSummary):

    items: List[InvoiceItemResponse] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Invoice List Response Schema
# Standard pagination response
# ----------------------------------------------------------------------

class InvoiceListResponse(BaseModel):

    items: List[InvoiceSummary]

    total: int

    page: int

    page_size: int

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------
# Invoice Filter Schema
# Used for filtering invoice records
# ----------------------------------------------------------------------

class InvoiceFilter(BaseModel):

    customer_id: Optional[int] = Field(
        default=None,
        gt=0
    )

    status: Optional[InvoiceStatus] = None

    date_from: Optional[datetime] = None

    date_to: Optional[datetime] = None

    page: int = Field(
        default=1,
        ge=1
    )

    page_size: int = Field(
        default=10,
        ge=1,
        le=100
    )
