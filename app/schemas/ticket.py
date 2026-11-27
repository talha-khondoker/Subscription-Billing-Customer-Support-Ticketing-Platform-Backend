# ----------------------------------------------------------------------
# app/schemas/ticket.py
# Owner:   Member 5
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------


"""Ticket schemas. Owner: Member 5. (Phase 2 + Phase 3 - replaces the Phase 2 file.)"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.enums import (
    AttemptStatus, BillingPeriod, InvoiceStatus, PaymentStatus, RefundStatus, Role,
    SubscriptionStatus, TicketCategory, TicketPriority, TicketStatus,
)
from app.schemas.customer import TicketSummary
from app.utils.dates import utcnow


# ------------------------------------------------------------------ requests
class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    category: TicketCategory = TicketCategory.GENERAL
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    """Only the fields that are sent are changed. Use /resolve and /escalate for those statuses."""
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None


class AssignRequest(BaseModel):
    agent_id: int


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class EscalateRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class ResolveRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=5000)  # shown to the customer


# ------------------------------------------------------------------ responses
class MessageOut(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_name: str
    sender_role: Role
    body: str
    is_internal: bool
    created_at: datetime

    @classmethod
    def from_message(cls, message) -> "MessageOut":
        """Build from a TicketMessage whose .sender is loaded."""
        return cls(
            id=message.id,
            ticket_id=message.ticket_id,
            sender_id=message.sender_id,
            sender_name=message.sender.full_name,
            sender_role=message.sender.role,
            body=message.body,
            is_internal=message.is_internal,
            created_at=message.created_at,
        )


class TicketOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    subject: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    assigned_agent_id: Optional[int] = None
    assigned_agent_name: Optional[str] = None
    first_response_due: Optional[datetime] = None
    resolution_due: Optional[datetime] = None
    first_responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    first_response_breached: bool
    resolution_breached: bool
    # SLA countdown in seconds. Negative = overdue. None = no deadline or already done.
    first_response_remaining_seconds: Optional[int] = None
    resolution_remaining_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_ticket(cls, ticket) -> "TicketOut":
        """Build from a Ticket whose .customer.user and .assigned_agent are loaded."""
        now = utcnow()
        finished = ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)

        first_remaining = None
        if ticket.first_response_due and ticket.first_responded_at is None and not finished:
            first_remaining = int((ticket.first_response_due - now).total_seconds())
        resolution_remaining = None
        if ticket.resolution_due and ticket.resolved_at is None and not finished:
            resolution_remaining = int((ticket.resolution_due - now).total_seconds())

        agent = ticket.assigned_agent
        return cls(
            id=ticket.id,
            customer_id=ticket.customer_id,
            customer_name=ticket.customer.user.full_name,
            subject=ticket.subject,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            assigned_agent_id=ticket.assigned_agent_id,
            assigned_agent_name=agent.full_name if agent else None,
            first_response_due=ticket.first_response_due,
            resolution_due=ticket.resolution_due,
            first_responded_at=ticket.first_responded_at,
            resolved_at=ticket.resolved_at,
            first_response_breached=ticket.first_response_breached,
            resolution_breached=ticket.resolution_breached,
            first_response_remaining_seconds=first_remaining,
            resolution_remaining_seconds=resolution_remaining,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class TicketDetailOut(TicketOut):
    description: str
    messages: List[MessageOut] = []

    @classmethod
    def build(cls, ticket, include_internal: bool) -> "TicketDetailOut":
        """Ticket + conversation. include_internal=False hides internal notes (customers)."""
        base = TicketOut.from_ticket(ticket).model_dump()
        messages = [
            MessageOut.from_message(m) for m in ticket.messages if include_internal or not m.is_internal
        ]
        return cls(**base, description=ticket.description, messages=messages)


# ------------------------------------------------------------------ Billing-to-Ticket View
class BillingCustomer(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    company_name: Optional[str] = None


class BillingSubscription(BaseModel):
    id: int
    plan_id: int
    plan_name: str
    plan_price: Decimal
    billing_period: BillingPeriod
    status: SubscriptionStatus
    current_period_end: datetime
    next_billing_date: Optional[datetime] = None
    cancel_at_period_end: bool


class BillingInvoice(BaseModel):
    id: int
    invoice_number: str
    total: Decimal
    status: InvoiceStatus
    issued_at: datetime
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class BillingPayment(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    status: PaymentStatus
    failure_reason: Optional[str] = None
    created_at: datetime


class BillingAttempt(BaseModel):
    id: int
    payment_id: int
    invoice_id: int
    attempt_number: int
    status: AttemptStatus
    gateway_response: Optional[dict] = None
    attempted_at: datetime
    next_retry_at: Optional[datetime] = None


class BillingRefund(BaseModel):
    id: int
    payment_id: int
    invoice_id: int
    amount: Decimal
    reason: Optional[str] = None
    status: RefundStatus
    created_at: datetime


class BillingContextOut(BaseModel):
    ticket_id: int
    customer: BillingCustomer
    alerts: List[str] = []                       # short warnings for the agent
    subscription: Optional[BillingSubscription] = None
    invoices: List[BillingInvoice] = []          # last 5
    payments: List[BillingPayment] = []          # last 5
    failed_attempt_count: int = 0                # all failed attempts of this customer
    failed_attempts: List[BillingAttempt] = []   # last 5
    refunds: List[BillingRefund] = []            # last 5
    past_tickets: List[TicketSummary] = []       # last 5, excluding this one
