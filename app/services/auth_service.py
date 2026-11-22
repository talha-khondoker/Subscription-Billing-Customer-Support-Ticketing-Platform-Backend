# ----------------------------------------------------------------------
# app/services/auth_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - register_customer(db, data)
#   - authenticate(db, email, password)
#   - build_token_response(user)

# ----------------------------------------------------------------------
# app/services/auth_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OrganizationStatus, Role
from app.core.exceptions import BusinessRuleError, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


def register_customer(db: Session, data: RegisterRequest) -> User:
    normalized_email = data.email.strip().lower()

    if db.scalar(select(User).where(User.email == normalized_email)):
        raise BusinessRuleError(
            detail="Email is already registered",
            code="email_already_exists",
        )

    organization = db.get(Organization, data.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise BusinessRuleError(
            detail="Organization not found or inactive",
            code="invalid_organization",
        )

    user = User(
        organization_id=organization.id,
        email=normalized_email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=Role.CUSTOMER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("Incorrect email or password")

    if user.organization_id is not None:
        organization = db.get(Organization, user.organization_id)
        if organization is None or organization.status != OrganizationStatus.ACTIVE:
            raise Unauthorized("Organization is disabled")

    return user


def build_token_response(user: User) -> TokenResponse:
    token = create_access_token(user.id, user.role, user.organization_id)
    return TokenResponse(access_token=token, token_type="bearer", user=user)
