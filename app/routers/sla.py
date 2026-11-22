# ----------------------------------------------------------------------
# app/routers/sla.py
# Owner:   Member 5
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /sla-policies [OA]
#   - GET   /sla-policies [OA]
#   - PATCH /sla-policies/{id} [OA]


"""SLA policy endpoints (Org Admin). Owner: Member 5. Paths are full; main.py adds /api/v1."""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_org_admin
from app.models.user import User
from app.schemas.sla import SlaPolicyCreate, SlaPolicyOut, SlaPolicyUpdate
from app.services import sla_service

router = APIRouter(tags=["sla"])


@router.post("/sla-policies", response_model=SlaPolicyOut, status_code=status.HTTP_201_CREATED)
def create_sla_policy(data: SlaPolicyCreate, db: Session = Depends(get_db), user: User = Depends(current_org_admin)):
    return sla_service.create_policy(db, user, data)


@router.get("/sla-policies", response_model=List[SlaPolicyOut])
def list_sla_policies(db: Session = Depends(get_db), user: User = Depends(current_org_admin)):
    return sla_service.list_policies(db, user)


@router.patch("/sla-policies/{policy_id}", response_model=SlaPolicyOut)
def update_sla_policy(
    policy_id: int, data: SlaPolicyUpdate, db: Session = Depends(get_db), user: User = Depends(current_org_admin)
):
    return sla_service.update_policy(db, user, policy_id, data)
