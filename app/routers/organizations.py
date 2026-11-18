# ----------------------------------------------------------------------
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.enums import Role
from app.core.exceptions import BusinessRuleError
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationOut, OrganizationUpdate
from app.schemas.common import Page
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])
super_admin = require_roles(Role.SUPER_ADMIN)


@router.post("", response_model=OrganizationOut, status_code=201)
def create(data: OrganizationCreate, db: Session = Depends(get_db), actor: User = Depends(super_admin)):
    try:
        result = organization_service.create_organization_with_admin(db, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=Page[OrganizationOut])
def list_all(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
             db: Session = Depends(get_db), actor: User = Depends(super_admin)):
    return organization_service.list_organizations(db, page, page_size)


@router.patch("/{organization_id}", response_model=OrganizationOut)
def update(organization_id: int, data: OrganizationUpdate, db: Session = Depends(get_db),
           actor: User = Depends(super_admin)):
    try:
        result = organization_service.update_organization(db, organization_id, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise
# app/routers/organizations.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /organizations [SA]  create organization + first Org Admin
#   - GET   /organizations [SA]  list
#   - PATCH /organizations/{id} [SA]  edit name / enable / disable
