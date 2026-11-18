# ----------------------------------------------------------------------
# app/services/customer_service.py
# Owner:   Member 6
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - get_my_profile / update_my_profile
#   - list_customers(db, org_id, search, page)
#   - get_customer_detail(db, id)  -> histories


"""Customer profiles and history. Owner: Member 6.

Every query filters by the caller's organization_id (tenant isolation).
"""
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFound
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.customer import (
    CustomerDetailOut,
    CustomerOut,
    CustomerUpdate,
    InvoiceSummary,
    PaymentSummary,
    SubscriptionSummary,
    TicketSummary,
)
from app.utils.pagination import paginate

HISTORY_LIMIT = 20  # newest N rows per history list in the detail view


# ---------------------------------------------------------------- customer (self)
def get_my_customer(db: Session, user: User) -> Customer:
    customer = db.scalar(
        select(Customer).options(selectinload(Customer.user)).where(Customer.user_id == user.id)
    )
    if customer is None:
        raise NotFound("Customer profile not found")
    return customer


def get_my_profile(db: Session, user: User) -> CustomerOut:
    return CustomerOut.from_customer(get_my_customer(db, user))


def update_my_profile(db: Session, user: User, data: CustomerUpdate) -> CustomerOut:
    customer = get_my_customer(db, user)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("full_name"):
        customer.user.full_name = changes["full_name"]
    if "phone" in changes:
        customer.phone = changes["phone"]
    if "company_name" in changes:
        customer.company_name = changes["company_name"]

    db.commit()
    db.refresh(customer)
    return CustomerOut.from_customer(customer)


# ---------------------------------------------------------------- staff views (Org Admin, Agent)
def _get_in_org(db: Session, user: User, customer_id: int) -> Customer:
    customer = db.scalar(
        select(Customer)
        .options(selectinload(Customer.user))
        .where(Customer.id == customer_id, Customer.organization_id == user.organization_id)
    )
    if customer is None:
        raise NotFound("Customer not found")
    return customer


def list_customers(
    db: Session, user: User, search: Optional[str] = None, page: int = 1, page_size: int = 20
) -> dict:
    stmt = (
        select(Customer)
        .join(User, Customer.user_id == User.id)
        .options(selectinload(Customer.user))
        .where(Customer.organization_id == user.organization_id)
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                Customer.company_name.ilike(pattern),
                Customer.phone.ilike(pattern),
            )
        )
    stmt = stmt.order_by(Customer.id.desc())

    result = paginate(db, stmt, page, page_size)
    result["items"] = [CustomerOut.from_customer(c) for c in result["items"]]
    return result


def get_customer_detail(db: Session, user: User, customer_id: int) -> CustomerDetailOut:
    customer = _get_in_org(db, user, customer_id)

    subscription_rows = db.execute(
        select(Subscription, Plan.name)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.customer_id == customer.id)
        .order_by(Subscription.id.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    invoices = db.scalars(
        select(Invoice).where(Invoice.customer_id == customer.id).order_by(Invoice.id.desc()).limit(HISTORY_LIMIT)
    ).all()
    payments = db.scalars(
        select(Payment).where(Payment.customer_id == customer.id).order_by(Payment.id.desc()).limit(HISTORY_LIMIT)
    ).all()
    tickets = db.scalars(
        select(Ticket).where(Ticket.customer_id == customer.id).order_by(Ticket.id.desc()).limit(HISTORY_LIMIT)
    ).all()

    base = CustomerOut.from_customer(customer)
    return CustomerDetailOut(
        **base.model_dump(),
        subscriptions=[
            SubscriptionSummary(
                id=s.id,
                plan_id=s.plan_id,
                plan_name=plan_name,
                status=s.status,
                current_period_end=s.current_period_end,
                next_billing_date=s.next_billing_date,
            )
            for s, plan_name in subscription_rows
        ],
        invoices=[
            InvoiceSummary(id=i.id, invoice_number=i.invoice_number, total=i.total, status=i.status, issued_at=i.issued_at)
            for i in invoices
        ],
        payments=[
            PaymentSummary(
                id=p.id, invoice_id=p.invoice_id, amount=p.amount, status=p.status,
                failure_reason=p.failure_reason, created_at=p.created_at,
            )
            for p in payments
        ],
        tickets=[
            TicketSummary(id=t.id, subject=t.subject, priority=t.priority, status=t.status, created_at=t.created_at)
            for t in tickets
        ],
    )
