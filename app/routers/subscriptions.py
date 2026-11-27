# ----------------------------------------------------------------------
# app/routers/subscriptions.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix /api/v1 is added by main.py.

from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_customer, current_staff, require_roles
from app.core.enums import Role, SubscriptionStatus
from app.models.user import User
from app.schemas.subscription import CancelRequest, ChangePlanRequest, SubscriptionCreate, SubscriptionOut
from app.services import subscription_service as svc

router = APIRouter(tags=["subscriptions"])
out = SubscriptionOut.from_subscription


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(request: SubscriptionCreate, db: Session = Depends(get_db),
                        user: User = Depends(current_customer)):
    return out(svc.create_subscription(db, user, request.plan_id))


@router.get("/subscriptions/me", response_model=List[SubscriptionOut])
def get_my_subscription(db: Session = Depends(get_db), user: User = Depends(current_customer)):
    return [out(s) for s in svc.get_my_subscriptions(db, user)]


@router.get("/subscriptions", response_model=List[SubscriptionOut])
def get_subscriptions(subscription_status: Optional[SubscriptionStatus] = None, plan_id: Optional[int] = None,
                      customer_id: Optional[int] = None, db: Session = Depends(get_db),
                      user: User = Depends(current_staff)):
    return [out(s) for s in svc.get_subscriptions(db, user, subscription_status, plan_id, customer_id)]


@router.post("/subscriptions/{subscription_id}/change-plan", response_model=SubscriptionOut)
def change_plan(subscription_id: int, request: ChangePlanRequest, db: Session = Depends(get_db),
                user: User = Depends(current_customer)):
    return out(svc.change_plan(db, user, subscription_id, request.new_plan_id))


@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionOut)
def pause_subscription(subscription_id: int, db: Session = Depends(get_db), user: User = Depends(current_customer)):
    return out(svc.pause_subscription(db, user, subscription_id))


@router.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionOut)
def resume_subscription(subscription_id: int, db: Session = Depends(get_db), user: User = Depends(current_customer)):
    return out(svc.resume_subscription(db, user, subscription_id))


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionOut)
def cancel_subscription(subscription_id: int, request: Optional[CancelRequest] = None, db: Session = Depends(get_db),
                        user: User = Depends(require_roles(Role.CUSTOMER, Role.ORG_ADMIN))):
    at_period_end = request.at_period_end if request else True
    return out(svc.cancel_subscription(db, user, subscription_id, at_period_end))
