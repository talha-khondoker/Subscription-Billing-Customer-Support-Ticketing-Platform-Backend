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



from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


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
    plan_id: int
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

    model_config = ConfigDict(from_attributes=True)
