
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
import calendar
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import BillingPeriod, SubscriptionStatus
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.utils.dates import utcnow


# ----------------------------------------------------------------------
# Helper 1: Database Commit with Rollback
# ----------------------------------------------------------------------

def save_changes(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


# ----------------------------------------------------------------------
# Helper 2: Calculate Next Billing Date
# ----------------------------------------------------------------------

def get_next_billing_date(start_date: datetime, billing_period):

    period = getattr(billing_period, "value", billing_period)
    period = str(period).lower()

    if period == "monthly":
        month_index = start_date.month

        year = start_date.year + month_index // 12
        month = month_index % 12 + 1

        day = min(
            start_date.day,
            calendar.monthrange(year, month)[1]
        )

        return start_date.replace(
            year=year,
            month=month,
            day=day
        )

    elif period == "yearly":
        year = start_date.year + 1

        day = min(
            start_date.day,
            calendar.monthrange(year, start_date.month)[1]
        )

        return start_date.replace(
            year=year,
            day=day
        )

    raise HTTPException(
        status_code=400,
        detail="Unsupported billing period"
    )


# ----------------------------------------------------------------------
# Helper 3: Get Customer Subscription
# ----------------------------------------------------------------------

def get_customer_subscription(
    db: Session,
    subscription_id: int,
    customer_id: int
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.customer_id == customer_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    return subscription


# ----------------------------------------------------------------------
# Helper 4: Get Active Plan
# ----------------------------------------------------------------------

def get_active_plan(
    db: Session,
    plan_id: int,
    organization_id: int
):
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.organization_id == organization_id,
        Plan.is_active.is_(True)
    ).first()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Active plan not found in your organization"
        )

    return plan


# ----------------------------------------------------------------------
# 1. Create Subscription
# ----------------------------------------------------------------------

def create_subscription(
    db: Session,
    customer_id: int,
    plan_id: int
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    plan = get_active_plan(
        db=db,
        plan_id=plan_id,
        organization_id=customer.organization_id
    )

    current_period_start = utcnow()

    current_period_end = get_next_billing_date(
        current_period_start,
        plan.billing_period
    )

    subscription = Subscription(
        organization_id=customer.organization_id,
        customer_id=customer.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=current_period_start,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        next_billing_date=current_period_end,
        cancel_at_period_end=False
    )

    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    except Exception:
        db.rollback()
        raise


# ----------------------------------------------------------------------
# 2. Change Subscription Plan
# ----------------------------------------------------------------------

def change_plan(
    db: Session,
    subscription_id: int,
    new_plan_id: int,
    customer_id: int
):
    subscription = get_customer_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer_id
    )

    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Only active subscriptions can change plan"
        )

    new_plan = get_active_plan(
        db=db,
        plan_id=new_plan_id,
        organization_id=subscription.organization_id
    )

    subscription.plan_id = new_plan.id

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 3. Pause Subscription
# ----------------------------------------------------------------------

def pause_subscription(
    db: Session,
    subscription_id: int,
    customer_id: int
):
    subscription = get_customer_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer_id
    )

    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Only active subscriptions can be paused"
        )

    subscription.status = SubscriptionStatus.PAUSED
    subscription.paused_at = utcnow()

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 4. Resume Subscription
# ----------------------------------------------------------------------

def resume_subscription(
    db: Session,
    subscription_id: int,
    customer_id: int
):
    subscription = get_customer_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer_id
    )

    if subscription.status != SubscriptionStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail="Only paused subscriptions can be resumed"
        )

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.paused_at = None

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 5. Cancel Subscription (CUSTOMER)
# ----------------------------------------------------------------------

def cancel_subscription(
    db: Session,
    subscription_id: int,
    customer_id: int,
    at_period_end: bool = True
):
    subscription = get_customer_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer_id
    )

    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Subscription already cancelled"
        )

    if at_period_end:
        subscription.cancel_at_period_end = True
    else:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = utcnow()
        subscription.cancel_at_period_end = False

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 6. Cancel Subscription (ORG ADMIN)
# ----------------------------------------------------------------------

def cancel_subscription_by_admin(
    db: Session,
    subscription_id: int,
    organization_id: int,
    at_period_end: bool = True
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.organization_id == organization_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Subscription already cancelled"
        )

    if at_period_end:
        subscription.cancel_at_period_end = True
    else:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = utcnow()
        subscription.cancel_at_period_end = False

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 7. Renew Subscription
# ----------------------------------------------------------------------

def renew_subscription(
    db: Session,
    subscription_id: int
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Only active subscriptions can be renewed"
        )

    if subscription.cancel_at_period_end:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = utcnow()
        subscription.cancel_at_period_end = False

        save_changes(db)
        db.refresh(subscription)

        return subscription

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Subscription plan not found"
        )

    new_start = subscription.current_period_end

    new_end = get_next_billing_date(
        new_start,
        plan.billing_period
    )

    subscription.current_period_start = new_start
    subscription.current_period_end = new_end
    subscription.next_billing_date = new_end

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 8. Mark Subscription Past Due
# ----------------------------------------------------------------------

def mark_past_due(
    db: Session,
    subscription_id: int
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Only active subscriptions can be marked past due"
        )

    subscription.status = SubscriptionStatus.PAST_DUE

    save_changes(db)
    db.refresh(subscription)

    return subscription


# ----------------------------------------------------------------------
# 9. Get My Subscriptions (CUSTOMER)
# ----------------------------------------------------------------------

def get_my_subscriptions(
    db: Session,
    customer_id: int
):
    subscriptions = db.query(Subscription).filter(
        Subscription.customer_id == customer_id
    ).all()

    return subscriptions


# ----------------------------------------------------------------------
# 10. Get / Filter Subscriptions
# ----------------------------------------------------------------------

def get_subscriptions(
    db: Session,
    subscription_status: str = None,
    plan_id: int = None
):
    query = db.query(Subscription)

    if subscription_status:
        query = query.filter(
            Subscription.status == subscription_status
        )

    if plan_id:
        query = query.filter(
            Subscription.plan_id == plan_id
        )

    return query.all()
