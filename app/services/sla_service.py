# ----------------------------------------------------------------------
# app/services/sla_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Defaults: Urgent 15 min / 4 h, High 1 h / 8 h, Medium 4 h / 24 h, Low 8 h / 72 h.


"""SLA policies, deadlines and breach checking. Owner: Member 5.
(Phase 2 + Phase 3 - replaces the Phase 2 file.)

Deadlines are plain elapsed minutes from ticket creation (no business hours).
Editing a policy does NOT change deadlines of tickets that already exist.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, TicketPriority, TicketStatus
from app.core.exceptions import BusinessRuleError, Conflict, NotFound
from app.models.sla_policy import SlaPolicy
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.sla import SlaPolicyCreate, SlaPolicyUpdate
from app.services import notification_service
from app.utils.dates import utcnow

# When a ticket newly breaches an SLA deadline, also move it to "escalated".
# Set to False if the team wants breach flags and notifications only.
AUTO_ESCALATE_ON_BREACH = True

FINISHED_STATUSES = [TicketStatus.RESOLVED, TicketStatus.CLOSED]


# ---------------------------------------------------------------- policy CRUD (Org Admin)
def list_policies(db: Session, user: User) -> List[SlaPolicy]:
    return list(
        db.scalars(
            select(SlaPolicy).where(SlaPolicy.organization_id == user.organization_id).order_by(SlaPolicy.id)
        ).all()
    )


def _get_in_org(db: Session, user: User, policy_id: int) -> SlaPolicy:
    policy = db.scalar(
        select(SlaPolicy).where(SlaPolicy.id == policy_id, SlaPolicy.organization_id == user.organization_id)
    )
    if policy is None:
        raise NotFound("SLA policy not found")
    return policy


def create_policy(db: Session, user: User, data: SlaPolicyCreate) -> SlaPolicy:
    existing = db.scalar(
        select(SlaPolicy.id).where(
            SlaPolicy.organization_id == user.organization_id, SlaPolicy.priority == data.priority
        )
    )
    if existing is not None:
        raise Conflict(f"A policy for '{data.priority.value}' priority already exists. Edit it instead.")

    policy = SlaPolicy(organization_id=user.organization_id, **data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(db: Session, user: User, policy_id: int, data: SlaPolicyUpdate) -> SlaPolicy:
    policy = _get_in_org(db, user, policy_id)
    changes = data.model_dump(exclude_unset=True)

    first = changes.get("first_response_minutes", policy.first_response_minutes)
    resolution = changes.get("resolution_minutes", policy.resolution_minutes)
    if resolution < first:
        raise BusinessRuleError("resolution_minutes must be >= first_response_minutes")

    for field, value in changes.items():
        if value is None:  # none of these columns accept NULL
            continue
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


# ---------------------------------------------------------------- used by ticket creation / update
def get_policy_for_priority(db: Session, organization_id: int, priority: TicketPriority) -> Optional[SlaPolicy]:
    """The active policy for a priority, or None when the organization has none."""
    return db.scalar(
        select(SlaPolicy).where(
            SlaPolicy.organization_id == organization_id,
            SlaPolicy.priority == priority,
            SlaPolicy.is_active.is_(True),
        )
    )


def apply_deadlines(ticket: Ticket, policy: Optional[SlaPolicy], start: datetime) -> None:
    """Set sla_policy_id, first_response_due and resolution_due on a ticket.

    With no policy the ticket simply has no deadlines (all three fields become None).
    """
    if policy is None:
        ticket.sla_policy_id = None
        ticket.first_response_due = None
        ticket.resolution_due = None
        return
    ticket.sla_policy_id = policy.id
    ticket.first_response_due = start + timedelta(minutes=policy.first_response_minutes)
    ticket.resolution_due = start + timedelta(minutes=policy.resolution_minutes)


# ---------------------------------------------------------------- SLA job
def check_breaches(db: Session) -> dict:
    """Flag tickets that passed an SLA deadline, notify, and (optionally) escalate them.

    Called by jobs/sla_job.py every few minutes and by POST /admin/jobs/run-sla-check.
    Each breach is flagged once; running it again does not repeat notifications.
    Commits at the end (it is a complete use case of its own).
    """
    now = utcnow()
    stmt = select(Ticket).where(
        Ticket.status.not_in(FINISHED_STATUSES),
        or_(
            and_(
                Ticket.first_responded_at.is_(None),
                Ticket.first_response_due.is_not(None),
                Ticket.first_response_due < now,
                Ticket.first_response_breached.is_(False),
            ),
            and_(
                Ticket.resolved_at.is_(None),
                Ticket.resolution_due.is_not(None),
                Ticket.resolution_due < now,
                Ticket.resolution_breached.is_(False),
            ),
        ),
    )
    tickets = db.scalars(stmt).all()

    summary = {"checked": len(tickets), "first_response_breaches": 0, "resolution_breaches": 0, "escalated": 0}
    for ticket in tickets:
        reasons = []
        if (ticket.first_responded_at is None and ticket.first_response_due
                and ticket.first_response_due < now and not ticket.first_response_breached):
            ticket.first_response_breached = True
            summary["first_response_breaches"] += 1
            reasons.append("first response")
        if (ticket.resolved_at is None and ticket.resolution_due
                and ticket.resolution_due < now and not ticket.resolution_breached):
            ticket.resolution_breached = True
            summary["resolution_breaches"] += 1
            reasons.append("resolution")
        if not reasons:
            continue

        title = f"SLA breach: ticket #{ticket.id}"
        message = f"Ticket #{ticket.id} '{ticket.subject}' missed its {' and '.join(reasons)} deadline."
        if ticket.assigned_agent_id is not None:
            notification_service.notify(
                db, ticket.assigned_agent_id, title, message, NotificationType.SLA,
                organization_id=ticket.organization_id,
            )
        notification_service.notify_org_admins(db, ticket.organization_id, title, message, NotificationType.SLA)

        if AUTO_ESCALATE_ON_BREACH and ticket.status != TicketStatus.ESCALATED:
            ticket.status = TicketStatus.ESCALATED
            summary["escalated"] += 1

    db.commit()
    return summary
