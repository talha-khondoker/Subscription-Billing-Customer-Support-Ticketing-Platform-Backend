# ----------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.exceptions import BusinessRuleError, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User


def register_customer(db: Session, data):
    if db.scalar(select(User).where(User.email == data.email)):
        raise BusinessRuleError("Email is already registered", 409, "EMAIL_EXISTS")
    organization = db.get(Organization, data.organization_id)
    if organization is None or str(organization.status) != "active":
        raise BusinessRuleError("Organization is unavailable", 404, "ORGANIZATION_NOT_FOUND")
    user = User(organization_id=organization.id, email=data.email.lower(),
                password_hash=hash_password(data.password), full_name=data.full_name,
                role=Role.CUSTOMER, is_active=True)
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("Incorrect email or password")
    if user.organization_id is not None:
        organization = db.get(Organization, user.organization_id)
        if organization is None or str(organization.status) != "active":
            raise Unauthorized("Organization is disabled")
    return user


def build_token_response(user):
    from app.schemas.auth import TokenResponse
    token = create_access_token(user.id, user.role, user.organization_id)
    return TokenResponse(access_token=token, user=user)
# app/services/auth_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - register_customer(db, data)
#   - authenticate(db, email, password)
#   - build_token_response(user)
