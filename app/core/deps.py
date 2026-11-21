
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import OrganizationStatus, Role
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token

from app.models.organization import Organization
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    if credentials is None:
        raise Unauthorized("Not authenticated")

    payload = decode_token(credentials.credentials)

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise Unauthorized("Invalid token")

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise Unauthorized("User not found or inactive")

    if user.organization_id is not None:

        organization = db.get(Organization, user.organization_id)

        if (
            organization is None
            or organization.status != OrganizationStatus.ACTIVE
        ):
            raise Forbidden("Your organization is disabled")

    return user


def require_roles(*roles: Role | str):

    allowed = {Role(role) for role in roles}

    def dependency(
        user: User = Depends(get_current_user)
    ) -> User:

        if user.role not in allowed:
            raise Forbidden(
                "You do not have permission for this action"
            )

        return user

    return dependency


# Convenience dependencies

current_super_admin = require_roles(Role.SUPER_ADMIN)
current_org_admin = require_roles(Role.ORG_ADMIN)
current_agent = require_roles(Role.AGENT)
current_customer = require_roles(Role.CUSTOMER)

current_staff = require_roles(
    Role.ORG_ADMIN,
    Role.AGENT)