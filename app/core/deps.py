# ----------------------------------------------------------------------
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models.organization import Organization
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Unauthorized("Invalid authentication token") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("User is inactive or does not exist")
    if user.organization_id is not None:
        organization = db.get(Organization, user.organization_id)
        if organization is None or str(organization.status) != "active":
            raise Unauthorized("Organization is disabled")
    return user


def require_roles(*roles):
    allowed = {str(role.value if isinstance(role, Role) else role) for role in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if str(user.role) not in allowed:
            raise Forbidden("You do not have permission to perform this action")
        return user

    return dependency


current_org_admin = require_roles(Role.ORG_ADMIN)
current_agent = require_roles(Role.AGENT)
current_customer = require_roles(Role.CUSTOMER)
# app/core/deps.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Reusable FastAPI dependencies for authentication and role checks.
# ----------------------------------------------------------------------
# TODO:
#   - get_current_user: read bearer token, load the user, reject inactive users and disabled organizations
#   - require_roles(*roles): dependency factory that returns 403 when the role is not allowed
#   - convenience dependencies: current_org_admin, current_agent, current_customer
