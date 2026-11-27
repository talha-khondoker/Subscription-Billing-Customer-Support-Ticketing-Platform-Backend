# ----------------------------------------------------------------------
# app/services/user_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.exceptions import BusinessRuleError, NotFound
from app.core.security import hash_password
from app.models.user import User


def create_agent(db: Session, org_id: int, data):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise BusinessRuleError("Email is already registered", 409, "EMAIL_EXISTS")
    user = User(organization_id=org_id, email=data.email.lower(), password_hash=hash_password(data.password),
                full_name=data.full_name, role=Role.AGENT, is_active=True)
    db.add(user)
    db.flush()
    return user


def list_agents(db: Session, org_id: int):
    return db.scalars(select(User).where(User.organization_id == org_id, User.role == Role.AGENT)
                      .order_by(User.id)).all()


def update_user(db: Session, org_id: int, user_id: int, data):
    user = db.scalar(select(User).where(User.id == user_id, User.organization_id == org_id))
    if user is None:
        raise NotFound("User not found")
    if user.role != Role.AGENT:
        raise BusinessRuleError("Only support agents can be updated here", 400, "NOT_AN_AGENT")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.flush()
    return user
