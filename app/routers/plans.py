# ----------------------------------------------------------------------
# app/routers/plans.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix /api/v1 is added by main.py.
#   The organization always comes from the logged-in user (never from the URL).

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_org_admin, require_roles
from app.core.enums import Role
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanOut, PlanUpdate
from app.services.plan_service import create_plan, list_plans, update_plan

router = APIRouter(tags=["plans"])


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan_route(plan_data: PlanCreate, db: Session = Depends(get_db),
                      user: User = Depends(current_org_admin)):
    return create_plan(db, plan_data, user.organization_id, actor=user)


@router.get("/plans", response_model=list[PlanOut])
def get_plans_route(db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.ORG_ADMIN, Role.AGENT, Role.CUSTOMER))):
    """Org Admin sees every plan; agents and customers see active plans only."""
    return list_plans(db, user.organization_id, is_customer=user.role != Role.ORG_ADMIN)


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan_route(plan_id: int, plan_data: PlanUpdate, db: Session = Depends(get_db),
                      user: User = Depends(current_org_admin)):
    """Edit a plan or activate / deactivate it (is_active)."""
    return update_plan(db, plan_id, user.organization_id, plan_data, actor=user)
