# ----------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OrganizationStatus, Role
from app.core.exceptions import BusinessRuleError, NotFound
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User


def create_organization_with_admin(db: Session, data):
    if db.scalar(select(Organization).where(Organization.name == data.name)):
        raise BusinessRuleError("Organization name already exists", 409, "ORGANIZATION_EXISTS")
    if db.scalar(select(User).where(User.email == data.admin_email.lower())):
        raise BusinessRuleError("Email is already registered", 409, "EMAIL_EXISTS")
    organization = Organization(name=data.name, status=OrganizationStatus.ACTIVE)
    db.add(organization)
    db.flush()
    admin = User(organization_id=organization.id, email=data.admin_email.lower(),
                 password_hash=hash_password(data.admin_password), full_name=data.admin_full_name,
                 role=Role.ORG_ADMIN, is_active=True)
    db.add(admin)
    db.flush()
    return organization


def list_organizations(db: Session, page=1, page_size=10):
    from app.utils.pagination import paginate
    return paginate(db.query(Organization).order_by(Organization.id), page, page_size)


def update_organization(db: Session, id: int, data):
    organization = db.get(Organization, id)
    if organization is None:
        raise NotFound("Organization not found")
    values = data.model_dump(exclude_unset=True)
    if "name" in values and db.scalar(select(Organization).where(
            Organization.name == values["name"], Organization.id != id)):
        raise BusinessRuleError("Organization name already exists", 409, "ORGANIZATION_EXISTS")
    for key, value in values.items():
        setattr(organization, key, value)
    db.flush()
    return organization
# app/services/organization_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_organization_with_admin(db, data)
#   - list_organizations(db, page)
#   - update_organization(db, id, data)  (disable blocks logins)
