# ----------------------------------------------------------------------
# app/routers/plans.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /plans [OA]  create
#   - GET   /plans [OA, AG, CU]  list (customers see active only)
#   - PATCH /plans/{id} [OA]  edit or activate/deactivate


# app/routers/plans.py

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.models.plan import get_db


from app.schemas.plan import (PlanCreate,PlanUpdate,PlanOut)

from app.services.plan_service import (create_plan,update_plan,list_plans,set_plan_active)
router = APIRouter(prefix="/api/v1/plans",tags=["Plans"])

db_dependency = Annotated[Session,Depends(get_db)]


# 1. Create Plan
@router.post("",response_model=PlanOut,status_code=status.HTTP_201_CREATED)
def create_plan_route( plan_data: PlanCreate, organization_id: int, db: db_dependency):
    return create_plan( db, plan_data, organization_id )


# 2. Get All Plans
@router.get("",response_model=list[PlanOut])
def get_plans_route(organization_id: int,db: db_dependency):

    return list_plans(db,organization_id)

# 3. Update Plan
@router.put("/{plan_id}",response_model=PlanOut)
def update_plan_route(plan_id: int, organization_id: int,plan_data: PlanUpdate,db: db_dependency):

    return update_plan( db, plan_id, organization_id, plan_data)
# 4. Active / Inactive Plan
@router.put("/{plan_id}/status", response_model=PlanOut)
def update_plan_status( plan_id: int, organization_id: int,is_active: bool, db: db_dependency):

    return set_plan_active( db, plan_id,  organization_id,  is_active)
