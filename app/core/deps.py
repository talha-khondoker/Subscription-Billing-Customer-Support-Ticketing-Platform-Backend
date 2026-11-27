# ----------------------------------------------------------------------
# app/core/deps.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Reusable FastAPI dependencies for authentication and role checks.
# ----------------------------------------------------------------------


"""Reusable FastAPI dependencies: authentication and role checks. Owner: Member 1.

Usage in a router:

    from app.core.deps import get_current_user, require_roles, current_agent
    from app.core.enums import Role

    @router.get("/tickets")
    def list_tickets(user: User = Depends(require_roles(Role.CUSTOMER, Role.AGENT, Role.ORG_ADMIN)),
                     db: Session = Depends(get_db)): ...

    @router.post("/tickets/{id}/escalate")
    def escalate(id: int, user: User = Depends(current_agent), db: Session = Depends(get_db)): ...

Swagger: click "Authorize" and paste the token only (no "Bearer " prefix).
"""

from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import OrganizationStatus, Role
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise Unauthorized("Invalid authentication token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("User not found or inactive")

    if user.organization_id is not None:
        organization = db.get(Organization, user.organization_id)
        if organization is None or organization.status != OrganizationStatus.ACTIVE:
            raise Forbidden("Your organization is disabled")

    # Safety net: a customer account must always have its Customer profile row.
    if user.role == Role.CUSTOMER and user.organization_id is not None and user.customer_profile is None:
        db.add(Customer(organization_id=user.organization_id, user_id=user.id))
        db.commit()
        db.refresh(user)

    return user


def require_roles(*roles: Role | str):
    allowed = {Role(role) for role in roles}

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise Forbidden("You do not have permission for this action")
        return user

    return dependency


current_super_admin = require_roles(Role.SUPER_ADMIN)
current_org_admin = require_roles(Role.ORG_ADMIN)
current_agent = require_roles(Role.AGENT)
current_customer = require_roles(Role.CUSTOMER)
current_staff = require_roles(Role.ORG_ADMIN, Role.AGENT)
