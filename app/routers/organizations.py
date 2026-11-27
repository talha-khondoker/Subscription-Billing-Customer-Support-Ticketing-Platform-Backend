# ----------------------------------------------------------------------
# app/routers/organizations.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.enums import Role
from app.core.exceptions import BusinessRuleError
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate, OrganizationOut, OrganizationPublic, OrganizationSelfUpdate, OrganizationUpdate,
)
from app.schemas.common import Page
from app.services import organization_service

router = APIRouter(tags=["organizations"])
super_admin = require_roles(Role.SUPER_ADMIN)


@router.get("/organizations/public", response_model=list[OrganizationPublic])
def public_list(db: Session = Depends(get_db)):
    """Public: active organizations (id + name) for the customer sign-up dropdown."""
    return organization_service.list_public_organizations(db)


@router.get("/organizations/me", response_model=OrganizationOut)
def my_organization(db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.ORG_ADMIN, Role.AGENT, Role.CUSTOMER))):
    return organization_service.get_my_organization(db, user)


@router.patch("/organizations/me", response_model=OrganizationOut)
def update_my_organization(data: OrganizationSelfUpdate, db: Session = Depends(get_db),
                           user: User = Depends(require_roles(Role.ORG_ADMIN))):
    try:
        result = organization_service.update_my_organization(db, user, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create(data: OrganizationCreate, db: Session = Depends(get_db), actor: User = Depends(super_admin)):
    try:
        result = organization_service.create_organization_with_admin(db, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/organizations", response_model=Page[OrganizationOut])
def list_all(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
             db: Session = Depends(get_db), actor: User = Depends(super_admin)):
    return organization_service.list_organizations(db, page, page_size)


@router.patch("/organizations/{organization_id}", response_model=OrganizationOut)
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
