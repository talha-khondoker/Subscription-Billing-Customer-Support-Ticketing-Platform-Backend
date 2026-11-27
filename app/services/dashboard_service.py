# ----------------------------------------------------------------------
# app/services/dashboard_service.py
# Owner:   Member 6
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------


"""Dashboard numbers. Owner: Member 6. Read-only.

Definitions (keep these in the demo notes):
    MRR   = sum of plan prices of ACTIVE subscriptions, yearly plans divided by 12
    ARR   = MRR x 12  (computed from unrounded values)
    Churn = subscriptions cancelled in the period / subscriptions that existed (and were not
            cancelled) at the start of the period, as a percentage
    Failed payments = payments that are in status 'failed' right now
    Recovered       = payments that succeeded in the period after at least one failed attempt
    SLA met %       = among tickets created in the period whose deadline already passed or was
                      answered: share answered/resolved in time
Plan prices are the plans' current prices (no custom discounts).
"""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    AttemptStatus, BillingPeriod, InvoiceStatus, OrganizationStatus, PaymentStatus, RefundStatus,
    Role, SubscriptionStatus, TicketPriority, TicketStatus,
)
from app.core.exceptions import Forbidden
from app.models import (
    Customer, Invoice, Organization, Payment, PaymentAttempt, Plan, Refund, Subscription, Ticket, User,
)
from app.schemas.customer import InvoiceSummary, PaymentSummary, SubscriptionSummary, TicketSummary
from app.schemas.dashboard import (
    AdminDashboard, AgentDashboard, CustomerDashboard, MonthRevenue, OrganizationRow, PaymentStats,
    PlatformDashboard, RevenueOverview, SlaPerformance, SubscriptionStats, TicketStats,
)
from app.schemas.ticket import TicketOut
from app.services import customer_service, notification_service
from app.services.assignment_service import OPEN_STATUSES
from app.utils.dates import add_months, utcnow
from app.utils.money import to_money

FINISHED = [TicketStatus.RESOLVED, TicketStatus.CLOSED]
ZERO = Decimal("0")


# ================================================================ small helpers
def _require(user: User, *roles: Role) -> None:
    if user.role not in roles:
        raise Forbidden("You do not have access to this dashboard")


def _dec(value) -> Decimal:
    return Decimal(str(value)) if value is not None else ZERO


def _percent(part: int, whole: int) -> Optional[float]:
    return round(part * 100 / whole, 1) if whole else None


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def _priority_counts(db: Session, *conditions) -> dict:
    """{'low': n, 'medium': n, 'high': n, 'urgent': n} for OPEN tickets matching the conditions."""
    rows = db.execute(
        select(Ticket.priority, func.count()).where(*conditions, Ticket.status.in_(OPEN_STATUSES)).group_by(Ticket.priority)
    ).all()
    result = {p.value: 0 for p in TicketPriority}
    for priority, count in rows:
        result[priority.value] = count
    return result


def _mrr_arr(db: Session, organization_id: Optional[int] = None):
    """(mrr, arr) of ACTIVE subscriptions, optionally for one organization."""
    stmt = (
        select(Plan.billing_period, func.coalesce(func.sum(Plan.price), 0))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
        .group_by(Plan.billing_period)
    )
    if organization_id is not None:
        stmt = stmt.where(Subscription.organization_id == organization_id)
    totals = {period: _dec(total) for period, total in db.execute(stmt).all()}
    monthly = totals.get(BillingPeriod.MONTHLY, ZERO)
    yearly = totals.get(BillingPeriod.YEARLY, ZERO)
    mrr = monthly + yearly / 12
    arr = monthly * 12 + yearly
    return to_money(mrr), to_money(arr)


def _sla_performance(db: Session, scope: tuple, since) -> SlaPerformance:
    """SLA numbers for tickets in `scope` (org / agent conditions) created since `since`."""
    in_period = (*scope, Ticket.created_at >= since)

    fr_base = (*in_period, Ticket.first_response_due.is_not(None),
               or_(Ticket.first_responded_at.is_not(None), Ticket.first_response_breached.is_(True)))
    fr_measured = _count(db, Ticket, *fr_base)
    fr_met = _count(db, Ticket, *fr_base, Ticket.first_responded_at.is_not(None),
                    Ticket.first_response_breached.is_(False))

    res_base = (*in_period, Ticket.resolution_due.is_not(None),
                or_(Ticket.resolved_at.is_not(None), Ticket.resolution_breached.is_(True)))
    res_measured = _count(db, Ticket, *res_base)
    res_met = _count(db, Ticket, *res_base, Ticket.resolved_at.is_not(None),
                     Ticket.resolution_breached.is_(False))

    breached_open = _count(
        db, Ticket, *scope, Ticket.status.in_(OPEN_STATUSES),
        or_(Ticket.first_response_breached.is_(True), Ticket.resolution_breached.is_(True)),
    )
    return SlaPerformance(
        first_response_met_percent=_percent(fr_met, fr_measured),
        resolution_met_percent=_percent(res_met, res_measured),
        first_response_measured=fr_measured,
        resolution_measured=res_measured,
        breached_open_tickets=breached_open,
    )


def _revenue_by_month(db: Session, organization_id: int, months: int = 6) -> list:
    now = utcnow()
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts = [add_months(first_this_month, -i) for i in range(months - 1, -1, -1)]
    totals = {f"{s.year}-{s.month:02d}": ZERO for s in starts}

    rows = db.execute(
        select(Invoice.paid_at, Invoice.total).where(
            Invoice.organization_id == organization_id,
            Invoice.status.in_([InvoiceStatus.PAID, InvoiceStatus.REFUNDED]),
            Invoice.paid_at.is_not(None),
            Invoice.paid_at >= starts[0],
        )
    ).all()
    for paid_at, total in rows:
        key = f"{paid_at.year}-{paid_at.month:02d}"
        if key in totals:
            totals[key] += _dec(total)
    return [MonthRevenue(month=m, revenue=to_money(v)) for m, v in totals.items()]


# ================================================================ Org Admin
def admin_dashboard(db: Session, user: User, days: int = 30) -> AdminDashboard:
    _require(user, Role.ORG_ADMIN)
    org = user.organization_id
    now = utcnow()
    since = now - timedelta(days=days)

    # --- revenue
    mrr, arr = _mrr_arr(db, org)
    collected = _dec(db.scalar(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.organization_id == org,
            Invoice.status.in_([InvoiceStatus.PAID, InvoiceStatus.REFUNDED]),
            Invoice.paid_at >= since, Invoice.paid_at <= now,
        )
    ))
    refunded = _dec(db.scalar(
        select(func.coalesce(func.sum(Refund.amount), 0)).where(
            Refund.organization_id == org, Refund.status == RefundStatus.COMPLETED, Refund.created_at >= since,
        )
    ))
    revenue = RevenueOverview(
        mrr=mrr, arr=arr, collected=to_money(collected), refunded=to_money(refunded),
        net=to_money(collected - refunded), by_month=_revenue_by_month(db, org),
    )

    # --- subscriptions
    by_status = dict(db.execute(
        select(Subscription.status, func.count()).where(Subscription.organization_id == org).group_by(Subscription.status)
    ).all())
    base = (
        Subscription.organization_id == org,
        Subscription.start_date < since,
        or_(Subscription.cancelled_at.is_(None), Subscription.cancelled_at >= since),
    )
    base_count = _count(db, Subscription, *base)
    churned = _count(db, Subscription, *base, Subscription.cancelled_at.is_not(None), Subscription.cancelled_at >= since)
    subscriptions = SubscriptionStats(
        active=by_status.get(SubscriptionStatus.ACTIVE, 0),
        paused=by_status.get(SubscriptionStatus.PAUSED, 0),
        past_due=by_status.get(SubscriptionStatus.PAST_DUE, 0),
        new_in_period=_count(db, Subscription, Subscription.organization_id == org, Subscription.start_date >= since),
        cancelled_in_period=_count(
            db, Subscription, Subscription.organization_id == org,
            Subscription.cancelled_at.is_not(None), Subscription.cancelled_at >= since,
        ),
        churn_rate_percent=_percent(churned, base_count),
    )

    # --- payments
    failed_count, failed_amount = db.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.organization_id == org, Payment.status == PaymentStatus.FAILED
        )
    ).one()
    recovered_count, recovered_amount = db.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.organization_id == org,
            Payment.status == PaymentStatus.SUCCEEDED,
            Payment.updated_at >= since,
            exists().where(PaymentAttempt.payment_id == Payment.id, PaymentAttempt.status == AttemptStatus.FAILED),
        )
    ).one()
    payments = PaymentStats(
        failed_count=failed_count, failed_amount=to_money(_dec(failed_amount)),
        recovered_count=recovered_count, recovered_amount=to_money(_dec(recovered_amount)),
    )

    # --- tickets
    scope = (Ticket.organization_id == org,)
    tickets = TicketStats(
        open=_count(db, Ticket, *scope, Ticket.status.in_(OPEN_STATUSES)),
        unassigned=_count(db, Ticket, *scope, Ticket.status.in_(OPEN_STATUSES), Ticket.assigned_agent_id.is_(None)),
        escalated=_count(db, Ticket, *scope, Ticket.status == TicketStatus.ESCALATED),
        created_in_period=_count(db, Ticket, *scope, Ticket.created_at >= since),
        resolved_in_period=_count(db, Ticket, *scope, Ticket.resolved_at.is_not(None), Ticket.resolved_at >= since),
        open_by_priority=_priority_counts(db, *scope),
    )

    return AdminDashboard(
        period_days=days, generated_at=now, revenue=revenue, subscriptions=subscriptions,
        payments=payments, tickets=tickets, sla=_sla_performance(db, scope, since),
    )


# ================================================================ Agent
def agent_dashboard(db: Session, user: User, days: int = 7) -> AgentDashboard:
    _require(user, Role.AGENT)
    now = utcnow()
    since = now - timedelta(days=days)
    scope = (Ticket.organization_id == user.organization_id, Ticket.assigned_agent_id == user.id)

    status_rows = dict(db.execute(
        select(Ticket.status, func.count()).where(*scope, Ticket.status.in_(OPEN_STATUSES)).group_by(Ticket.status)
    ).all())
    open_by_status = {s.value: status_rows.get(s, 0) for s in OPEN_STATUSES}

    open_tickets = db.scalars(
        select(Ticket)
        .options(selectinload(Ticket.customer).selectinload(Customer.user), selectinload(Ticket.assigned_agent))
        .where(*scope, Ticket.status.in_(OPEN_STATUSES))
    ).all()
    outs = [TicketOut.from_ticket(t) for t in open_tickets]

    def urgency(out: TicketOut):
        remaining = [r for r in (out.first_response_remaining_seconds, out.resolution_remaining_seconds) if r is not None]
        return (0, min(remaining)) if remaining else (1, 0)   # closest / most overdue deadline first

    return AgentDashboard(
        period_days=days,
        generated_at=now,
        open_tickets=sum(open_by_status.values()),
        waiting_customer=open_by_status[TicketStatus.WAITING_CUSTOMER.value],
        escalated=open_by_status[TicketStatus.ESCALATED.value],
        overdue=_count(db, Ticket, *scope, Ticket.status.in_(OPEN_STATUSES),
                       or_(Ticket.first_response_breached.is_(True), Ticket.resolution_breached.is_(True))),
        resolved_in_period=_count(db, Ticket, *scope, Ticket.resolved_at.is_not(None), Ticket.resolved_at >= since),
        open_by_priority=_priority_counts(db, *scope),
        open_by_status=open_by_status,
        sla=_sla_performance(db, scope, since),
        needs_attention=sorted(outs, key=urgency)[:10],
    )


# ================================================================ Customer
def customer_dashboard(db: Session, user: User) -> CustomerDashboard:
    _require(user, Role.CUSTOMER)
    customer = customer_service.get_my_customer(db, user)

    rows = db.execute(
        select(Subscription, Plan.name)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.customer_id == customer.id)
        .order_by(Subscription.id.desc())
    ).all()
    chosen = next((r for r in rows if r[0].status != SubscriptionStatus.CANCELLED), rows[0] if rows else None)
    subscription = None
    if chosen is not None:
        sub, plan_name = chosen
        subscription = SubscriptionSummary(
            id=sub.id, plan_id=sub.plan_id, plan_name=plan_name, status=sub.status,
            current_period_end=sub.current_period_end, next_billing_date=sub.next_billing_date,
        )

    unpaid = (Invoice.customer_id == customer.id, Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.FAILED]))
    unpaid_count, amount_due = db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(*unpaid)
    ).one()

    invoices = db.scalars(select(Invoice).where(Invoice.customer_id == customer.id).order_by(Invoice.id.desc()).limit(5)).all()
    payments = db.scalars(select(Payment).where(Payment.customer_id == customer.id).order_by(Payment.id.desc()).limit(5)).all()
    tickets = db.scalars(select(Ticket).where(Ticket.customer_id == customer.id).order_by(Ticket.id.desc()).limit(5)).all()

    return CustomerDashboard(
        subscription=subscription,
        open_tickets=_count(db, Ticket, Ticket.customer_id == customer.id, Ticket.status.in_(OPEN_STATUSES)),
        unpaid_invoice_count=unpaid_count,
        amount_due=to_money(_dec(amount_due)),
        has_failed_payment=_count(db, Payment, Payment.customer_id == customer.id, Payment.status == PaymentStatus.FAILED) > 0,
        unread_notifications=notification_service.unread_count(db, user),
        recent_invoices=[InvoiceSummary(id=i.id, invoice_number=i.invoice_number, total=i.total,
                                        status=i.status, issued_at=i.issued_at) for i in invoices],
        recent_payments=[PaymentSummary(id=p.id, invoice_id=p.invoice_id, amount=p.amount, status=p.status,
                                        failure_reason=p.failure_reason, created_at=p.created_at) for p in payments],
        recent_tickets=[TicketSummary(id=t.id, subject=t.subject, priority=t.priority, status=t.status,
                                      created_at=t.created_at) for t in tickets],
    )


# ================================================================ Super Admin
def platform_dashboard(db: Session, user: User) -> PlatformDashboard:
    _require(user, Role.SUPER_ADMIN)

    organizations = db.scalars(select(Organization)).all()
    customers_by_org = dict(db.execute(
        select(Customer.organization_id, func.count()).group_by(Customer.organization_id)
    ).all())
    active_by_org = dict(db.execute(
        select(Subscription.organization_id, func.count())
        .where(Subscription.status == SubscriptionStatus.ACTIVE).group_by(Subscription.organization_id)
    ).all())

    mrr_rows = db.execute(
        select(Subscription.organization_id, Plan.billing_period, func.coalesce(func.sum(Plan.price), 0))
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
        .group_by(Subscription.organization_id, Plan.billing_period)
    ).all()
    mrr_by_org: dict = {}
    for org_id, period, total in mrr_rows:
        value = _dec(total) if period == BillingPeriod.MONTHLY else _dec(total) / 12
        mrr_by_org[org_id] = mrr_by_org.get(org_id, ZERO) + value

    rows = [
        OrganizationRow(
            id=o.id, name=o.name, status=o.status,
            customers=customers_by_org.get(o.id, 0),
            active_subscriptions=active_by_org.get(o.id, 0),
            mrr=to_money(mrr_by_org.get(o.id, ZERO)),
        )
        for o in organizations
    ]
    rows.sort(key=lambda r: (-r.mrr, r.name))

    platform_mrr, platform_arr = _mrr_arr(db)
    role_counts = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())

    return PlatformDashboard(
        generated_at=utcnow(),
        organizations_total=len(organizations),
        organizations_active=sum(1 for o in organizations if o.status == OrganizationStatus.ACTIVE),
        organizations_disabled=sum(1 for o in organizations if o.status == OrganizationStatus.DISABLED),
        total_users=sum(role_counts.values()),
        users_by_role={r.value: role_counts.get(r, 0) for r in Role},
        total_customers=sum(customers_by_org.values()),
        active_subscriptions=sum(active_by_org.values()),
        platform_mrr=platform_mrr,
        platform_arr=platform_arr,
        open_tickets=_count(db, Ticket, Ticket.status.in_(OPEN_STATUSES)),
        failed_payments=_count(db, Payment, Payment.status == PaymentStatus.FAILED),
        top_organizations=rows[:10],
    )
