# ----------------------------------------------------------------------
# app/routers/customers.py
# Owner:   Member 6
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET   /customers/me [CU]
#   - PATCH /customers/me [CU]
#   - GET   /customers [OA, AG]  with search
#   - GET   /customers/{id} [OA, AG]  profile + histories

"""Customer endpoints. Owner: Member 6. Paths are full paths; main.py adds /api/v1.

NOTE: /customers/me is declared BEFORE /customers/{customer_id} on purpose,
otherwise "me" would be parsed as a customer id.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.enums import Role
from app.models.user import User
from app.schemas.common import Page
from app.schemas.customer import CustomerDetailOut, CustomerOut, CustomerUpdate
from app.services import customer_service

router = APIRouter(tags=["customers"])


@router.get("/customers/me", response_model=CustomerOut)
def get_my_profile(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.CUSTOMER))):
    return customer_service.get_my_profile(db, user)


@router.patch("/customers/me", response_model=CustomerOut)
def update_my_profile(
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.CUSTOMER)),
):
    return customer_service.update_my_profile(db, user, data)


@router.get("/customers", response_model=Page[CustomerOut])
def list_customers(
    search: Optional[str] = Query(None, description="email, name, company or phone"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ORG_ADMIN, Role.AGENT)),
):
    return customer_service.list_customers(db, user, search, page, page_size)


@router.get("/customers/{customer_id}", response_model=CustomerDetailOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ORG_ADMIN, Role.AGENT)),
):
    return customer_service.get_customer_detail(db, user, customer_id)

