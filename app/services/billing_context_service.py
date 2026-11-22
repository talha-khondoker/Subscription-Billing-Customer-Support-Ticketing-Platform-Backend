# ----------------------------------------------------------------------
# app/services/billing_context_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Flagship feature: the Billing-to-Ticket View.
# TODO:
#   - get_billing_context(db, ticket)  -> subscription, last 5 invoices, last 5 payments, failed attempts, refunds, last 5 tickets




"""Billing-to-Ticket View (the flagship feature). Owner: Member 5.

One response with everything an agent needs about the customer's billing situation while
working on a ticket: subscription, last 5 invoices, last 5 payments, failed payment attempts,
refunds, past tickets, plus short alerts. Read-only.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AttemptStatus, InvoiceStatus, Role, SubscriptionStatus
from app.core.exceptions import Forbidden
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentAttempt, Refund
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.customer import TicketSummary
from app.schemas.ticket import (
    BillingAttempt, BillingContextOut, BillingCustomer, BillingInvoice, BillingPayment,
    BillingRefund, BillingSubscription,
)
from app.services import ticket_service
from app.utils.dates import utcnow

LIMIT = 5


def get_billing_context(db: Session, user: User, ticket_id: int) -> BillingContextOut:
    if user.role not in (Role.AGENT, Role.ORG_ADMIN):
        raise Forbidden("Only staff can view billing information")

    ticket = ticket_service.load_visible_ticket(db, user, ticket_id)  # also enforces visibility
    customer = ticket.customer
    now = utcnow()

    # --- subscription: newest one that is not cancelled, otherwise the newest overall
    sub_rows = db.execute(
        select(Subscription, Plan)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.customer_id == customer.id)
        .order_by(Subscription.id.desc())
    ).all()
    chosen = next((row for row in sub_rows if row[0].status != SubscriptionStatus.CANCELLED), None)
    if chosen is None and sub_rows:
        chosen = sub_rows[0]
    subscription = None
    if chosen is not None:
        sub, plan = chosen
        subscription = BillingSubscription(
            id=sub.id, plan_id=plan.id, plan_name=plan.name, plan_price=plan.price,
            billing_period=plan.billing_period, status=sub.status,
            current_period_end=sub.current_period_end, next_billing_date=sub.next_billing_date,
            cancel_at_period_end=sub.cancel_at_period_end,
        )

    # --- invoices, payments
    invoices = db.scalars(
        select(Invoice).where(Invoice.customer_id == customer.id).order_by(Invoice.id.desc()).limit(LIMIT)
    ).all()
    payments = db.scalars(
        select(Payment).where(Payment.customer_id == customer.id).order_by(Payment.id.desc()).limit(LIMIT)
    ).all()

    # --- failed attempts (last 5 + total count)
    failed_filter = (Payment.customer_id == customer.id, PaymentAttempt.status == AttemptStatus.FAILED)
    attempts = db.scalars(
        select(PaymentAttempt)
        .join(Payment, PaymentAttempt.payment_id == Payment.id)
        .where(*failed_filter)
        .order_by(PaymentAttempt.attempted_at.desc(), PaymentAttempt.id.desc())
        .limit(LIMIT)
    ).all()
    failed_count = db.scalar(
        select(func.count())
        .select_from(PaymentAttempt)
        .join(Payment, PaymentAttempt.payment_id == Payment.id)
        .where(*failed_filter)
    ) or 0

    # --- refunds, past tickets
    refunds = db.scalars(
        select(Refund)
        .join(Payment, Refund.payment_id == Payment.id)
        .where(Payment.customer_id == customer.id)
        .order_by(Refund.id.desc())
        .limit(LIMIT)
    ).all()
    past_tickets = db.scalars(
        select(Ticket)
        .where(Ticket.customer_id == customer.id, Ticket.id != ticket.id)
        .order_by(Ticket.id.desc())
        .limit(LIMIT)
    ).all()

    # --- alerts for the agent
    alerts = []
    if subscription is not None and subscription.status == SubscriptionStatus.PAST_DUE:
        alerts.append("Subscription is past due")
    if failed_count:
        alerts.append(f"{failed_count} failed payment attempt(s)")
    for invoice in invoices:
        if invoice.status == InvoiceStatus.OPEN and invoice.due_date and invoice.due_date < now:
            alerts.append(f"Overdue invoice {invoice.invoice_number}")

    return BillingContextOut(
        ticket_id=ticket.id,
        customer=BillingCustomer(
            id=customer.id, name=customer.user.full_name, email=customer.user.email,
            phone=customer.phone, company_name=customer.company_name,
        ),
        alerts=alerts,
        subscription=subscription,
        invoices=[
            BillingInvoice(id=i.id, invoice_number=i.invoice_number, total=i.total, status=i.status,
                           issued_at=i.issued_at, due_date=i.due_date, paid_at=i.paid_at)
            for i in invoices
        ],
        payments=[
            BillingPayment(id=p.id, invoice_id=p.invoice_id, amount=p.amount, status=p.status,
                           failure_reason=p.failure_reason, created_at=p.created_at)
            for p in payments
        ],
        failed_attempt_count=failed_count,
        failed_attempts=[
            BillingAttempt(id=a.id, payment_id=a.payment_id, invoice_id=a.invoice_id,
                           attempt_number=a.attempt_number, status=a.status,
                           gateway_response=a.gateway_response, attempted_at=a.attempted_at,
                           next_retry_at=a.next_retry_at)
            for a in attempts
        ],
        refunds=[
            BillingRefund(id=r.id, payment_id=r.payment_id, invoice_id=r.invoice_id, amount=r.amount,
                          reason=r.reason, status=r.status, created_at=r.created_at)
            for r in refunds
        ],
        past_tickets=[
            TicketSummary(id=t.id, subject=t.subject, priority=t.priority, status=t.status, created_at=t.created_at)
            for t in past_tickets
        ],
    )
