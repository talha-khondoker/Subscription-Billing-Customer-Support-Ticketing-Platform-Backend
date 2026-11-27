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
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import OrganizationRegisterRequest, ProfileUpdate, RegisterRequest, TokenResponse
from app.schemas.organization import OrganizationCreate
from app.services import organization_service


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
    # every customer account needs its Customer profile row
    db.add(Customer(organization_id=organization.id, user_id=user.id))
    db.flush()
    return user


def register_organization(db: Session, data: OrganizationRegisterRequest) -> User:
    """Public sign-up of an organization: creates it with its first Org Admin and default SLA policies."""
    organization = organization_service.create_organization_with_admin(
        db,
        OrganizationCreate(
            name=data.organization_name.strip(),
            admin_email=data.admin_email,
            admin_password=data.admin_password,
            admin_full_name=data.admin_full_name.strip(),
        ),
    )
    return db.scalar(select(User).where(User.organization_id == organization.id, User.role == Role.ORG_ADMIN))


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    db.flush()
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise BusinessRuleError(detail="Current password is incorrect", code="invalid_password")
    if verify_password(new_password, user.password_hash):
        raise BusinessRuleError(detail="New password must be different from the current one", code="same_password")
    user.password_hash = hash_password(new_password)
    db.flush()


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
