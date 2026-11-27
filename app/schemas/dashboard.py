# ----------------------------------------------------------------------
# app/schemas/dashboard.py
# Owner:   Member 6
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------


"""Dashboard schemas. Owner: Member 6."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.core.enums import OrganizationStatus
from app.schemas.customer import InvoiceSummary, PaymentSummary, SubscriptionSummary, TicketSummary
from app.schemas.ticket import TicketOut


# ------------------------------------------------------------------ shared pieces
class SlaPerformance(BaseModel):
    # Share of measured tickets (created in the period) that met the deadline. None = nothing measured yet.
    first_response_met_percent: Optional[float] = None
    resolution_met_percent: Optional[float] = None
    first_response_measured: int = 0
    resolution_measured: int = 0
    breached_open_tickets: int = 0   # currently open tickets that already missed a deadline


# ------------------------------------------------------------------ admin
class MonthRevenue(BaseModel):
    month: str        # "2026-11"
    revenue: Decimal


class RevenueOverview(BaseModel):
    mrr: Decimal                 # monthly recurring revenue (active subscriptions, yearly plans / 12)
    arr: Decimal                 # annual recurring revenue = MRR x 12
    collected: Decimal           # gross invoices paid in the period
    refunded: Decimal            # refunds issued in the period
    net: Decimal                 # collected - refunded
    by_month: List[MonthRevenue] # last 6 calendar months, oldest first


class SubscriptionStats(BaseModel):
    active: int
    paused: int
    past_due: int
    new_in_period: int
    cancelled_in_period: int
    churn_rate_percent: Optional[float] = None  # None when there were no subscriptions at the period start


class PaymentStats(BaseModel):
    failed_count: int            # payments that are failed right now (not yet recovered)
    failed_amount: Decimal
    recovered_count: int         # succeeded in the period after at least one failed attempt
    recovered_amount: Decimal


class TicketStats(BaseModel):
    open: int
    unassigned: int
    escalated: int
    created_in_period: int
    resolved_in_period: int
    open_by_priority: Dict[str, int]


class AdminDashboard(BaseModel):
    period_days: int
    generated_at: datetime
    revenue: RevenueOverview
    subscriptions: SubscriptionStats
    payments: PaymentStats
    tickets: TicketStats
    sla: SlaPerformance


# ------------------------------------------------------------------ agent
class AgentDashboard(BaseModel):
    period_days: int
    generated_at: datetime
    open_tickets: int
    waiting_customer: int
    escalated: int
    overdue: int                         # open tickets that already missed an SLA deadline
    resolved_in_period: int
    open_by_priority: Dict[str, int]
    open_by_status: Dict[str, int]
    sla: SlaPerformance
    needs_attention: List[TicketOut]     # up to 10 open tickets, closest SLA deadline first


# ------------------------------------------------------------------ customer
class CustomerDashboard(BaseModel):
    subscription: Optional[SubscriptionSummary] = None
    open_tickets: int
    unpaid_invoice_count: int
    amount_due: Decimal
    has_failed_payment: bool
    unread_notifications: int
    recent_invoices: List[InvoiceSummary] = []
    recent_payments: List[PaymentSummary] = []
    recent_tickets: List[TicketSummary] = []


# ------------------------------------------------------------------ platform (Super Admin)
class OrganizationRow(BaseModel):
    id: int
    name: str
    status: OrganizationStatus
    customers: int
    active_subscriptions: int
    mrr: Decimal


class PlatformDashboard(BaseModel):
    generated_at: datetime
    organizations_total: int
    organizations_active: int
    organizations_disabled: int
    total_users: int
    users_by_role: Dict[str, int]
    total_customers: int
    active_subscriptions: int
    platform_mrr: Decimal
    platform_arr: Decimal
    open_tickets: int
    failed_payments: int
    top_organizations: List[OrganizationRow]   # up to 10, highest MRR first
