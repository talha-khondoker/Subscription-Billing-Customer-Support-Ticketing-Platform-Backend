# ----------------------------------------------------------------------
# app/services/assignment_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - pick_agent(db, org_id)  -> active agent with the fewest open tickets


"""Automatic ticket assignment. Owner: Member 5."""
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.enums import Role, TicketStatus
from app.models.ticket import Ticket
from app.models.user import User

# A ticket counts toward an agent's workload until it is resolved or closed.
OPEN_STATUSES = [
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_CUSTOMER,
    TicketStatus.ESCALATED,
]


def pick_agent(db: Session, organization_id: int) -> Optional[User]:
    """Active agent of the organization with the fewest open tickets (ties: lowest user id).

    Returns None when the organization has no active agent.
    """
    open_count = func.count(Ticket.id)
    stmt = (
        select(User)
        .outerjoin(Ticket, and_(Ticket.assigned_agent_id == User.id, Ticket.status.in_(OPEN_STATUSES)))
        .where(
            User.organization_id == organization_id,
            User.role == Role.AGENT,
            User.is_active.is_(True),
        )
        .group_by(User.id)
        .order_by(open_count.asc(), User.id.asc())
        .limit(1)
    )
    return db.scalars(stmt).first()
