# ----------------------------------------------------------------------
# app/schemas/customer.py
# Owner:   Member 6
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - CustomerUpdate
#   - CustomerOut
#   - CustomerDetailOut (profile + subscription, invoice, payment, ticket history)

"""Customer schemas. Owner: Member 6."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus, TicketPriority, TicketStatus


class CustomerUpdate(BaseModel):
    """Only the fields that are sent are changed."""
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    company_name: Optional[str] = Field(default=None, max_length=150)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_customer(cls, customer) -> "CustomerOut":
        """Build from a Customer ORM object whose .user is loaded."""
        return cls(
            id=customer.id,
            user_id=customer.user_id,
            email=customer.user.email,
            full_name=customer.user.full_name,
            phone=customer.phone,
            company_name=customer.company_name,
            created_at=customer.created_at,
        )


# Small summaries used inside the customer detail view (newest first, limited).
class SubscriptionSummary(BaseModel):
    id: int
    plan_id: int
    plan_name: str
    status: SubscriptionStatus
    current_period_end: datetime
    next_billing_date: Optional[datetime] = None


class InvoiceSummary(BaseModel):
    id: int
    invoice_number: str
    total: Decimal
    status: InvoiceStatus
    issued_at: datetime


class PaymentSummary(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    status: PaymentStatus
    failure_reason: Optional[str] = None
    created_at: datetime


class TicketSummary(BaseModel):
    id: int
    subject: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime


class CustomerDetailOut(CustomerOut):
    subscriptions: List[SubscriptionSummary] = []
    invoices: List[InvoiceSummary] = []
    payments: List[PaymentSummary] = []
    tickets: List[TicketSummary] = []

