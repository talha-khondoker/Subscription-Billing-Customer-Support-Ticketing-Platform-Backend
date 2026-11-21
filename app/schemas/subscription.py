# ----------------------------------------------------------------------
# app/schemas/subscription.py
# Owner:   Member 2
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - SubscriptionCreate (plan_id)
#   - ChangePlanRequest (new_plan_id)
#   - CancelRequest (at_period_end)
#   - SubscriptionOut

# ----------------------------------------------------------------------
# app/schemas/subscription.py
# Owner: Member 2
# Purpose: Pydantic request/response schemas
# ----------------------------------------------------------------------

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.core.enums import SubscriptionStatus


# 1. Create Subscription Schema
class SubscriptionCreate(BaseModel):
    plan_id: int = Field(..., gt=0)


# 2. Change Plan Request Schema
class ChangePlanRequest(BaseModel):
    new_plan_id: int = Field(..., gt=0)


# 3. Cancel Subscription Schema
class CancelRequest(BaseModel):
    at_period_end: bool = True


# 4. Subscription Response Schema
class SubscriptionOut(BaseModel):
    id: int
    organization_id: int
    customer_id: int
    plan_id: int
    status: SubscriptionStatus

    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime

    next_billing_date: datetime | None = None
    paused_at: datetime | None = None
    cancelled_at: datetime | None = None

    cancel_at_period_end: bool = False

    model_config = ConfigDict(from_attributes=True)
