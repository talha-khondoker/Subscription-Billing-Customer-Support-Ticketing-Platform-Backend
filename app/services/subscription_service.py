# ----------------------------------------------------------------------
# app/services/subscription_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Status flow: active <-> paused; active -> past_due after last failed retry; any -> cancelled.
# TODO:
#   - create_subscription(db, customer, plan)  -> calls invoice_service then payment_service
#   - change_plan(db, subscription, new_plan)  -> uses proration_service
#   - pause / resume
#   - cancel(db, subscription, at_period_end)
#   - renew(db, subscription)  -> advance period, create invoice (used by renewal job)
#   - mark_past_due(db, subscription)



from datetime import datetime, timezone
from calendar import monthrange

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.subscription import Subscription

def get_next_billing_date(start_date, billing_period):

    period = getattr(billing_period, "value", billing_period)
    period = str(period).lower()

    if period == "monthly":
        month = start_date.month + 1
        year = start_date.year

        if month > 12:
            month = 1
            year += 1

        day = min( start_date.day, monthrange(year, month)[1])

        return start_date.replace(year=year, month=month,day=day)

    elif period == "yearly":
        year = start_date.year + 1
        day = min(start_date.day,monthrange(year, start_date.month)[1])
        return start_date.replace(year=year,day=day)
    else:
        raise ValueError("Unsupported billing period")

def create_subscription( db: Session,customer_id: int,plan_id: int):

    plan = db.query(Plan).filter(Plan.id == plan_id,Plan.is_active == True ).first()

    if plan is None:
        raise ValueError("Plan not found or inactive")

    now = datetime.now(timezone.utc)

    next_billing = get_next_billing_date(now,plan.billing_period)
    subscription = Subscription(
        organization_id=plan.organization_id,
        customer_id=customer_id,
        plan_id=plan.id,
        status="active",
        start_date=now,
        current_period_start=now,
        current_period_end=next_billing,
        next_billing_date=next_billing,
        cancel_at_period_end=False)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription

def change_plan(db: Session, subscription_id: int,new_plan_id: int):

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id ).first()

    if subscription is None:
        raise ValueError("Subscription not found")

    if subscription.status != "active":
        raise ValueError("Only active subscriptions can change plan")

    new_plan = db.query(Plan).filter(
        Plan.id == new_plan_id,
        Plan.is_active == True,
        Plan.organization_id == subscription.organization_id ).first()

    if new_plan is None:
        raise ValueError("New plan not found or inactive")

    subscription.plan_id = new_plan.id

    db.commit()
    db.refresh(subscription)

    return subscription

def pause_subscription(db: Session,subscription_id: int):

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    if subscription is None:
        raise ValueError("Subscription not found")

    if subscription.status != "active":
        raise ValueError("Only active subscriptions can be paused")

    subscription.status = "paused"
    subscription.paused_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(subscription)

    return subscription
def resume_subscription( db: Session,subscription_id: int):

    subscription = db.query(Subscription).filter( Subscription.id == subscription_id).first()

    if subscription is None:
        raise ValueError("Subscription not found")

    if subscription.status != "paused":
        raise ValueError("Only paused subscriptions can be resumed")

    subscription.status = "active"
    subscription.paused_at = None

    db.commit()
    db.refresh(subscription)

    return subscription

def cancel_subscription(db: Session,subscription_id: int,at_period_end: bool = True):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription is None:
        raise ValueError("Subscription not found")
    if subscription.status == "cancelled":
        raise ValueError("Subscription already cancelled")
    if at_period_end:
        subscription.cancel_at_period_end = True
    else:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.cancel_at_period_end = False
    db.commit()
    db.refresh(subscription)
    return subscription
def renew_subscription(db: Session,subscription_id: int):

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription is None:
        raise ValueError("Subscription not found")
    if subscription.status != "active":
        raise ValueError("Only active subscriptions can be renewed")

    if subscription.cancel_at_period_end:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(subscription)
        return subscription
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if plan is None:
        raise ValueError("Subscription plan not found")
    new_start = subscription.current_period_end
    new_end = get_next_billing_date( new_start,  plan.billing_period)
    subscription.current_period_start = new_start
    subscription.current_period_end = new_end
    subscription.next_billing_date = new_end
    db.commit()
    db.refresh(subscription)
    return subscription

def mark_past_due(db: Session,subscription_id: int):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription is None:
        raise ValueError("Subscription not found")
    if subscription.status != "active":
        raise ValueError("Only active subscriptions can become past_due")
    subscription.status = "past_due"
    db.commit()
    db.refresh(subscription)
    return subscription

def get_my_subscriptions(db: Session,customer_id: int):
    subscriptions = db.query(Subscription).filter(Subscription.customer_id == customer_id ).all()

    return subscriptions

def get_subscriptions(db: Session,subscription_status: str = None,plan_id: int = None):

    query = db.query(Subscription)

    if subscription_status:
        query = query.filter(Subscription.status == subscription_status)
    if plan_id:
        query = query.filter(Subscription.plan_id == plan_id)
    return query.all()
