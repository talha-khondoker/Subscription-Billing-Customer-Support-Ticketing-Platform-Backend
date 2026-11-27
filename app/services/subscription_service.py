# ----------------------------------------------------------------------
# app/services/subscription_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Status flow: active <-> paused; active -> past_due after last failed retry; any -> cancelled.
#   Every function checks the caller: customers only touch their own subscriptions, Org Admins
#   (cancel/list only) stay inside their organization.

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import InvoiceStatus, NotificationType, Role, SubscriptionStatus
from app.core.exceptions import BusinessRuleError, Conflict, Forbidden, NotFound
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services import audit_service, invoice_service, notification_service, payment_service
from app.services.proration_service import calculate_proration
from app.utils.dates import add_period, utcnow
from app.utils.money import to_money

LIVE = (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED, SubscriptionStatus.PAST_DUE)


def _options():
    return (selectinload(Subscription.customer).selectinload(Customer.user), selectinload(Subscription.plan))


def _my_customer(user: User) -> Customer:
    if user.customer_profile is None:
        raise NotFound("Customer profile not found")
    return user.customer_profile


def _load(db: Session, user: User, subscription_id: int, *, allow_admin: bool = False) -> Subscription:
    sub = db.scalar(
        select(Subscription).options(*_options()).where(
            Subscription.id == subscription_id, Subscription.organization_id == user.organization_id
        )
    )
    if sub is None:
        raise NotFound("Subscription not found")
    if user.role == Role.CUSTOMER:
        if sub.customer_id != _my_customer(user).id:
            raise NotFound("Subscription not found")
    elif user.role == Role.ORG_ADMIN:
        if not allow_admin:
            raise Forbidden("Only the customer can do this")
    else:
        raise Forbidden("You do not have permission for this action")
    return sub


# ---------------------------------------------------------------- create
def create_subscription(db: Session, user: User, plan_id: int) -> Subscription:
    """Customer subscribes: first invoice is created and paid through the mock gateway."""
    customer = _my_customer(user)
    plan = db.scalar(select(Plan).where(Plan.id == plan_id, Plan.organization_id == user.organization_id))
    if plan is None or not plan.is_active:
        raise NotFound("Plan not found or inactive")
    if db.scalar(select(Subscription.id).where(
            Subscription.customer_id == customer.id, Subscription.plan_id == plan.id,
            Subscription.status.in_(LIVE))):
        raise Conflict("You already have a subscription to this plan")

    now = utcnow()
    period_end = add_period(now, plan.billing_period)
    sub = Subscription(
        organization_id=plan.organization_id, customer_id=customer.id, plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE, start_date=now, current_period_start=now,
        current_period_end=period_end, next_billing_date=period_end, cancel_at_period_end=False,
    )
    db.add(sub)
    db.flush()

    invoice = invoice_service.generate_for_subscription(db, sub)
    audit_service.log(db, user, "subscription.create", "subscription", sub.id, None, {"plan_id": plan.id})
    notification_service.notify(db, user.id, "Subscription started", f"You subscribed to {plan.name}.",
                                NotificationType.BILLING, organization_id=sub.organization_id)
    notification_service.notify_org_admins(db, sub.organization_id, "New subscription",
                                           f"{user.full_name} subscribed to {plan.name}.", NotificationType.BILLING)
    if invoice.total <= 0:  # free plan: nothing to charge
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = now
        db.commit()
    else:
        payment_service.attempt_payment(db, invoice)  # commits (payment succeeded or retry scheduled)
    db.refresh(sub)
    return sub


# ---------------------------------------------------------------- change plan
def change_plan(db: Session, user: User, subscription_id: int, new_plan_id: int) -> Subscription:
    sub = _load(db, user, subscription_id)
    if sub.status != SubscriptionStatus.ACTIVE:
        raise BusinessRuleError("Only active subscriptions can change plan")
    new_plan = db.scalar(select(Plan).where(Plan.id == new_plan_id, Plan.organization_id == sub.organization_id))
    if new_plan is None or not new_plan.is_active:
        raise NotFound("New plan not found or inactive")
    old_plan = sub.plan
    if new_plan.id == old_plan.id:
        raise BusinessRuleError("You are already on this plan")

    now = utcnow()
    calc = calculate_proration(old_plan, new_plan, sub.current_period_start, sub.current_period_end, now)
    if new_plan.billing_period != old_plan.billing_period:
        # Different period length: unused part of the old plan is credited, the new plan starts a fresh period.
        net = to_money(to_money(new_plan.price) - calc["credit"])
        sub.current_period_start = now
        sub.current_period_end = add_period(now, new_plan.billing_period)
        sub.next_billing_date = sub.current_period_end
    else:
        net = calc["net"]

    old_values = {"plan_id": old_plan.id, "plan_name": old_plan.name}
    sub.plan = new_plan
    db.flush()

    invoice = invoice_service.build_proration_invoice(db, sub, net) if net != 0 else None
    audit_service.log(db, user, "subscription.change_plan", "subscription", sub.id, old_values,
                      {"plan_id": new_plan.id, "plan_name": new_plan.name, "proration_net": str(net)})
    notification_service.notify(db, user.id, "Plan changed", f"You moved from {old_plan.name} to {new_plan.name}.",
                                NotificationType.BILLING, organization_id=sub.organization_id)

    if invoice is not None and invoice.total > 0:
        payment_service.attempt_payment(db, invoice)  # commits
    else:
        if invoice is not None:  # net credit: record it as a settled credit invoice
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = now
        db.commit()
    db.refresh(sub)
    return sub


# ---------------------------------------------------------------- pause / resume / cancel
def pause_subscription(db: Session, user: User, subscription_id: int) -> Subscription:
    sub = _load(db, user, subscription_id)
    if sub.status != SubscriptionStatus.ACTIVE:
        raise BusinessRuleError("Only active subscriptions can be paused")
    sub.status = SubscriptionStatus.PAUSED
    sub.paused_at = utcnow()
    db.commit()
    db.refresh(sub)
    return sub


def resume_subscription(db: Session, user: User, subscription_id: int) -> Subscription:
    sub = _load(db, user, subscription_id)
    if sub.status != SubscriptionStatus.PAUSED:
        raise BusinessRuleError("Only paused subscriptions can be resumed")
    now = utcnow()
    if sub.paused_at is not None:  # the customer does not pay for the paused time
        pause_length = now - sub.paused_at
        sub.current_period_end = sub.current_period_end + pause_length
        if sub.next_billing_date is not None:
            sub.next_billing_date = sub.next_billing_date + pause_length
    sub.status = SubscriptionStatus.ACTIVE
    sub.paused_at = None
    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(db: Session, user: User, subscription_id: int, at_period_end: bool = True) -> Subscription:
    """Customer (own) or Org Admin (same organization) cancels."""
    sub = _load(db, user, subscription_id, allow_admin=True)
    if sub.status == SubscriptionStatus.CANCELLED:
        raise BusinessRuleError("Subscription already cancelled")

    old = {"status": sub.status.value, "cancel_at_period_end": sub.cancel_at_period_end}
    now = utcnow()
    # Only an active subscription can run until the end of the period; others are cancelled right away.
    if at_period_end and sub.status == SubscriptionStatus.ACTIVE:
        sub.cancel_at_period_end = True
        message = f"Your {sub.plan.name} subscription will end on {sub.current_period_end:%Y-%m-%d}."
    else:
        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = now
        sub.cancel_at_period_end = False
        sub.next_billing_date = None
        message = f"Your {sub.plan.name} subscription was cancelled."

    audit_service.log(db, user, "subscription.cancel", "subscription", sub.id, old,
                      {"status": sub.status.value, "cancel_at_period_end": sub.cancel_at_period_end})
    notification_service.notify(db, sub.customer.user_id, "Subscription cancellation", message,
                                NotificationType.BILLING, organization_id=sub.organization_id)
    db.commit()
    db.refresh(sub)
    return sub


# ---------------------------------------------------------------- renewal (used by renewal_job)
def renew(db: Session, subscription: Subscription):
    """Advance one billing period and create the renewal invoice.

    Returns the Invoice to be paid, or None when nothing is to be paid (the subscription ended
    because cancel_at_period_end was set, or the invoice total is zero). The caller pays the invoice.
    """
    if subscription.status != SubscriptionStatus.ACTIVE:
        return None
    now = utcnow()

    if subscription.cancel_at_period_end:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = now
        subscription.next_billing_date = None
        notification_service.notify(db, subscription.customer.user_id, "Subscription ended",
                                    f"Your {subscription.plan.name} subscription has ended.",
                                    NotificationType.BILLING, organization_id=subscription.organization_id)
        db.flush()
        return None

    plan = subscription.plan
    new_start = subscription.current_period_end
    subscription.current_period_start = new_start
    subscription.current_period_end = add_period(new_start, plan.billing_period)
    subscription.next_billing_date = subscription.current_period_end
    invoice = invoice_service.generate_for_subscription(db, subscription)
    if invoice.total <= 0:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = now
        db.flush()
        return None
    db.flush()
    return invoice


def mark_past_due(db: Session, subscription: Subscription) -> Subscription:
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise BusinessRuleError("Only active subscriptions can become past_due")
    subscription.status = SubscriptionStatus.PAST_DUE
    db.flush()
    return subscription


# ---------------------------------------------------------------- queries
def get_my_subscriptions(db: Session, user: User) -> List[Subscription]:
    customer = _my_customer(user)
    return list(db.scalars(
        select(Subscription).options(*_options())
        .where(Subscription.customer_id == customer.id).order_by(Subscription.id.desc())
    ).all())


def get_subscriptions(db: Session, user: User, status: Optional[SubscriptionStatus] = None,
                      plan_id: Optional[int] = None, customer_id: Optional[int] = None) -> List[Subscription]:
    stmt = select(Subscription).options(*_options()).where(Subscription.organization_id == user.organization_id)
    if status is not None:
        stmt = stmt.where(Subscription.status == status)
    if plan_id is not None:
        stmt = stmt.where(Subscription.plan_id == plan_id)
    if customer_id is not None:
        stmt = stmt.where(Subscription.customer_id == customer_id)
    return list(db.scalars(stmt.order_by(Subscription.id.desc())).all())
