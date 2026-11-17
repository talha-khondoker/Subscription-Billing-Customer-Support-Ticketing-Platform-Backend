# ----------------------------------------------------------------------
# app/schemas/payment.py
# Owner:   Member 4
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - PayInvoiceRequest
#   - PaymentOut
#   - PaymentAttemptOut
#   - RefundCreate (amount, reason)
#   - RefundOut
#   - MockGatewayConfig (mode: always_success | always_fail | random)


from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AttemptStatus, PaymentStatus, RefundStatus


class PayInvoiceRequest(BaseModel):
    invoice_id: int = Field(gt=0)

class PaymentAttemptOut(BaseModel):
    """A single payment gateway attempt."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    invoice_id: int
    attempt_number: int = Field(ge=1)
    status: AttemptStatus
    gateway_response: Optional[dict[str, Any]] = None
    attempted_at: datetime
    next_retry_at: Optional[datetime] = None

class PaymentOut(BaseModel):
    """Payment details returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    invoice_id: int
    customer_id: int
    amount: Decimal
    status: PaymentStatus
    gateway_reference: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RefundCreate(BaseModel):
    """Data required to create a refund."""

    amount: Decimal = Field(gt=0)
    reason: Optional[str] = Field(default=None, max_length=1000)


class RefundOut(BaseModel):
    """Refund details returned"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    payment_id: int
    invoice_id: int
    amount: Decimal
    reason: Optional[str] = None
    issued_by: int
    status: RefundStatus
    created_at: datetime
    updated_at: datetime


class MockGatewayConfig(BaseModel):
    """Configuration for mock payment gateway"""

    mode: Literal["always_success", "always_fail", "random"]
