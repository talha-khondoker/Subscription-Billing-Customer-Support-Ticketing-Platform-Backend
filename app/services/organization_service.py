# ----------------------------------------------------------------------
# app/services/organization_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OrganizationStatus, Role
from app.core.exceptions import BusinessRuleError, NotFound
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.sla_policy import SlaPolicy
from app.models.user import User
from app.core.enums import TicketPriority

# priority, first response minutes, resolution minutes (spec defaults)
DEFAULT_SLA = [
    (TicketPriority.URGENT, 15, 4 * 60),
    (TicketPriority.HIGH, 60, 8 * 60),
    (TicketPriority.MEDIUM, 4 * 60, 24 * 60),
    (TicketPriority.LOW, 8 * 60, 72 * 60),
]


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
    for priority, first_response, resolution in DEFAULT_SLA:
        db.add(SlaPolicy(organization_id=organization.id, name=f"{priority.value.title()} priority",
                         priority=priority, first_response_minutes=first_response,
                         resolution_minutes=resolution))
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


def list_public_organizations(db: Session):
    """Active organizations, for the customer sign-up dropdown (id + name only)."""
    return db.scalars(select(Organization).where(Organization.status == OrganizationStatus.ACTIVE)
                      .order_by(Organization.name)).all()


def get_my_organization(db: Session, user: User) -> Organization:
    organization = db.get(Organization, user.organization_id) if user.organization_id else None
    if organization is None:
        raise NotFound("Organization not found")
    return organization


def update_my_organization(db: Session, user: User, data) -> Organization:
    from app.services import audit_service
    organization = get_my_organization(db, user)
    name = data.name.strip()
    if db.scalar(select(Organization).where(Organization.name == name, Organization.id != organization.id)):
        raise BusinessRuleError("Organization name already exists", 409, "ORGANIZATION_EXISTS")
    old = {"name": organization.name}
    organization.name = name
    audit_service.log(db, user, "organization.update", "organization", organization.id, old, {"name": name})
    db.flush()
    return organization
