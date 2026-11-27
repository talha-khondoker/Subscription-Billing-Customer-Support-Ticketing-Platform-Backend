# ----------------------------------------------------------------------
# app/schemas/subscription.py
# Owner:   Member 2
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------



from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


# 1. Subscription Create Schema
class SubscriptionCreate(BaseModel):
    plan_id: int


# 2. Change Plan Request Schema
class ChangePlanRequest(BaseModel):
    new_plan_id: int


# 3. Cancel Subscription Schema
class CancelRequest(BaseModel):
    at_period_end: bool = True


# 4. Subscription Response Schema
class SubscriptionOut(BaseModel):
    id: int
    organization_id: int
    customer_id: int
    customer_name: Optional[str] = None
    plan_id: int
    plan_name: str
    plan_price: Decimal
    billing_period: str
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_subscription(cls, sub) -> "SubscriptionOut":
        """Build from a Subscription whose .plan and .customer.user can be loaded."""
        value = lambda e: getattr(e, "value", e)
        return cls(
            id=sub.id, organization_id=sub.organization_id, customer_id=sub.customer_id,
            customer_name=sub.customer.user.full_name if sub.customer and sub.customer.user else None,
            plan_id=sub.plan_id, plan_name=sub.plan.name, plan_price=sub.plan.price,
            billing_period=value(sub.plan.billing_period), status=value(sub.status),
            start_date=sub.start_date, current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end, next_billing_date=sub.next_billing_date,
            paused_at=sub.paused_at, cancelled_at=sub.cancelled_at,
            cancel_at_period_end=sub.cancel_at_period_end,
        )
