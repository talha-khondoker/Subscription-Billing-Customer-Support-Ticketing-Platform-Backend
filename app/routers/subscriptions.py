# ----------------------------------------------------------------------
# app/routers/subscriptions.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /subscriptions [CU]  subscribe (creates first invoice + payment)
#   - GET  /subscriptions/me [CU]
#   - GET  /subscriptions [OA, AG]  list with filters
#   - POST /subscriptions/{id}/change-plan [CU]
#   - POST /subscriptions/{id}/pause [CU]
#   - POST /subscriptions/{id}/resume [CU]
#   - POST /subscriptions/{id}/cancel [CU, OA]

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.subscription import (
    SubscriptionCreate,
    ChangePlanRequest,
    CancelRequest,
    SubscriptionOut
)
from app.services import subscription_service
router = APIRouter(prefix="/api/v1/subscriptions",tags=["Subscriptions"])
db_dependency = Annotated[Session,Depends(get_db)]
@router.post("",response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(request: SubscriptionCreate,db: db_dependency):
    try:
        subscription = subscription_service.create_subscription(db=db,customer_id=1,plan_id=request.plan_id)
        return subscription
    except ValueError as e:
        raise HTTPException( status_code=400,detail=str(e))

@router.get("/me",response_model=list[SubscriptionOut])
def get_my_subscription(db: db_dependency):
    subscriptions = subscription_service.get_my_subscriptions(db=db,  customer_id=1  )
    return subscriptions

@router.get("",response_model=list[SubscriptionOut])
def get_subscriptions(db: db_dependency,subscription_status: str | None = None,plan_id: int | None = None):
    subscriptions = subscription_service.get_subscriptions( db=db,subscription_status=subscription_status,plan_id=plan_id)

    return subscriptions

@router.post( "/{subscription_id}/change-plan", response_model=SubscriptionOut
)
def change_plan( subscription_id: int, request: ChangePlanRequest, db: db_dependency):

    try:
        subscription = subscription_service.change_plan( db=db, subscription_id=subscription_id, new_plan_id=request.new_plan_id)
        return subscription
    except ValueError as e:
        raise HTTPException( status_code=400, detail=str(e))
@router.post( "/{subscription_id}/pause",response_model=SubscriptionOut)
def pause_subscription( subscription_id: int,db: db_dependency):

    try:
        return subscription_service.pause_subscription( db=db,subscription_id=subscription_id)

    except ValueError as e:
        raise HTTPException( status_code=400,detail=str(e))

@router.post("/{subscription_id}/resume",response_model=SubscriptionOut)
def resume_subscription(subscription_id: int, db: db_dependency):
    try:
        return subscription_service.resume_subscription( db=db,subscription_id=subscription_id)
    except ValueError as e:
        raise HTTPException(  status_code=400, detail=str(e))
@router.post( "/{subscription_id}/cancel",response_model=SubscriptionOut)
def cancel_subscription(subscription_id: int, request: CancelRequest,db: db_dependency):
    try:
        return subscription_service.cancel_subscription(
            db=db, subscription_id=subscription_id,at_period_end=request.at_period_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e) )

