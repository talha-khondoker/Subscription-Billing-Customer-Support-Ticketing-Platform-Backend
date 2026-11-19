# ----------------------------------------------------------------------
# app/services/ticket_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_ticket(db, customer, data)  -> sla_service + assignment_service
#   - list_tickets(db, user, filters, page)
#   - get_ticket(db, user, id)  -> hide internal notes from customers
#   - update_ticket
#   - assign_ticket
#   - add_message  (agent reply sets first_responded_at)
#   - add_internal_note
#   - escalate_ticket
#   - resolve_ticket


"""Tickets. Owner: Member 5. (Phase 2 + Phase 3 - replaces the Phase 2 file.)

Visibility rules (always inside the caller's organization):
    Customer   -> only their own tickets
    Agent      -> only tickets assigned to them
    Org Admin  -> every ticket of the organization

Status flow:
    open -> in_progress <-> waiting_customer -> resolved -> closed
    escalated is set by /escalate (agent) or by the SLA job; resolved only by /resolve.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import NotificationType, Role, TicketCategory, TicketPriority, TicketStatus
from app.core.exceptions import BusinessRuleError, Forbidden, NotFound
from app.models.customer import Customer
from app.models.ticket import Ticket, TicketMessage
from app.models.user import User
from app.schemas.ticket import (
    AssignRequest, EscalateRequest, MessageCreate, MessageOut, ResolveRequest,
    TicketCreate, TicketDetailOut, TicketOut, TicketUpdate,
)
from app.services import assignment_service, notification_service, sla_service
from app.utils.dates import utcnow
from app.utils.pagination import paginate

FINISHED = (TicketStatus.RESOLVED, TicketStatus.CLOSED)

# Status changes allowed through PATCH /tickets/{id}.
# resolved -> /resolve endpoint, escalated -> /escalate endpoint (or the SLA job).
PATCH_STATUS_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CUSTOMER},
    TicketStatus.IN_PROGRESS: {TicketStatus.WAITING_CUSTOMER},
    TicketStatus.WAITING_CUSTOMER: {TicketStatus.IN_PROGRESS},
    TicketStatus.ESCALATED: {TicketStatus.IN_PROGRESS},
    TicketStatus.RESOLVED: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.CLOSED: set(),
}


# ================================================================ helpers
def _list_options():
    return (
        selectinload(Ticket.customer).selectinload(Customer.user),
        selectinload(Ticket.assigned_agent),
    )


def _detail_options():
    return _list_options() + (selectinload(Ticket.messages).selectinload(TicketMessage.sender),)


def _customer_id_of(db: Session, user: User) -> int:
    customer_id = db.scalar(select(Customer.id).where(Customer.user_id == user.id))
    if customer_id is None:
        raise NotFound("Customer profile not found")
    return customer_id


def _apply_visibility(db: Session, user: User, stmt):
    """Restrict a SELECT on Ticket to what this user may see."""
    stmt = stmt.where(Ticket.organization_id == user.organization_id)
    if user.role == Role.CUSTOMER:
        return stmt.where(Ticket.customer_id == _customer_id_of(db, user))
    if user.role == Role.AGENT:
        return stmt.where(Ticket.assigned_agent_id == user.id)
    if user.role == Role.ORG_ADMIN:
        return stmt
    raise Forbidden("You do not have access to tickets")


def _audit(db: Session, actor: User, action: str, ticket: Ticket, old: dict, new: dict) -> None:
    """Write an audit log entry when Member 1's audit_service is available.
    Expected signature: audit_service.log(db, actor, action, entity_type, entity_id, old, new)."""
    try:
        from app.services import audit_service
        log = audit_service.log
    except (ImportError, AttributeError):
        return
    log(db, actor, action, "ticket", ticket.id, old, new)


def _mark_first_response(ticket: Ticket, now) -> None:
    """First public staff reply: record the time and flag a late reply."""
    if ticket.first_responded_at is None:
        ticket.first_responded_at = now
        if ticket.first_response_due and now > ticket.first_response_due:
            ticket.first_response_breached = True


def _notify_customer(db: Session, ticket: Ticket, title: str, message: str) -> None:
    notification_service.notify(
        db, ticket.customer.user_id, title, message, NotificationType.TICKET,
        organization_id=ticket.organization_id,
    )


# ================================================================ create / list / get
def create_ticket(db: Session, user: User, data: TicketCreate) -> TicketDetailOut:
    """Customer creates a ticket: SLA deadlines are set and the least-busy agent is assigned."""
    customer_id = _customer_id_of(db, user)
    organization_id = user.organization_id
    now = utcnow()

    ticket = Ticket(
        organization_id=organization_id,
        customer_id=customer_id,
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=data.priority,
        status=TicketStatus.OPEN,
        created_at=now,
    )

    policy = sla_service.get_policy_for_priority(db, organization_id, data.priority)
    sla_service.apply_deadlines(ticket, policy, now)

    agent = assignment_service.pick_agent(db, organization_id)
    if agent is not None:
        ticket.assigned_agent_id = agent.id

    db.add(ticket)
    db.flush()  # ticket.id is needed for the notification text

    title = f"New ticket #{ticket.id}"
    message = f"{data.priority.value.title()} priority: {ticket.subject}"
    if agent is not None:
        notification_service.notify(
            db, agent.id, title, message, NotificationType.TICKET, organization_id=organization_id
        )
    else:
        notification_service.notify_org_admins(
            db, organization_id, f"{title} (unassigned)", message, NotificationType.TICKET
        )

    db.commit()
    return get_ticket(db, user, ticket.id)


def list_tickets(
    db: Session,
    user: User,
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    category: Optional[TicketCategory] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = _apply_visibility(db, user, select(Ticket).options(*_list_options()))
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if category is not None:
        stmt = stmt.where(Ticket.category == category)
    if search:
        stmt = stmt.where(Ticket.subject.ilike(f"%{search.strip()}%"))
    stmt = stmt.order_by(Ticket.id.desc())

    result = paginate_stmt(db, stmt, page, page_size)
    result["items"] = [TicketOut.from_ticket(t) for t in result["items"]]
    return result


def load_visible_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    """Ticket ORM object with relations loaded, or NotFound (also when it is not visible to the user)."""
    stmt = _apply_visibility(db, user, select(Ticket).options(*_detail_options()).where(Ticket.id == ticket_id))
    ticket = db.scalar(stmt)
    if ticket is None:
        raise NotFound("Ticket not found")
    return ticket


def get_ticket(db: Session, user: User, ticket_id: int) -> TicketDetailOut:
    ticket = load_visible_ticket(db, user, ticket_id)
    return TicketDetailOut.build(ticket, include_internal=user.role != Role.CUSTOMER)


# ================================================================ messages and notes
def add_message(db: Session, user: User, ticket_id: int, data: MessageCreate) -> MessageOut:
    """Public reply by the customer or the assigned agent.

    Agent reply : sets first_responded_at (once), open -> in_progress, notifies the customer.
    Customer    : waiting_customer -> in_progress; a reply on a resolved ticket reopens it;
                  notifies the assigned agent (or the Org Admins when unassigned).
    """
    if user.role not in (Role.CUSTOMER, Role.AGENT):
        raise Forbidden("Only the customer or the assigned agent can reply. Org Admins can add internal notes.")
    ticket = load_visible_ticket(db, user, ticket_id)
    if ticket.status == TicketStatus.CLOSED:
        raise BusinessRuleError("This ticket is closed. Please open a new ticket.")

    now = utcnow()
    message = TicketMessage(ticket_id=ticket.id, sender_id=user.id, body=data.body, is_internal=False)
    db.add(message)

    title = f"New reply on ticket #{ticket.id}"
    if user.role == Role.AGENT:
        _mark_first_response(ticket, now)
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        _notify_customer(db, ticket, title, f"Support replied to: {ticket.subject}")
    else:
        if ticket.status == TicketStatus.RESOLVED:
            ticket.status = TicketStatus.OPEN
            ticket.resolved_at = None
        elif ticket.status == TicketStatus.WAITING_CUSTOMER:
            ticket.status = TicketStatus.IN_PROGRESS
        text = f"{user.full_name} replied to: {ticket.subject}"
        if ticket.assigned_agent_id is not None:
            notification_service.notify(
                db, ticket.assigned_agent_id, title, text, NotificationType.TICKET,
                organization_id=ticket.organization_id,
            )
        else:
            notification_service.notify_org_admins(db, ticket.organization_id, title, text, NotificationType.TICKET)

    db.commit()
    db.refresh(message)
    return MessageOut.from_message(message)


def add_internal_note(db: Session, user: User, ticket_id: int, data: MessageCreate) -> MessageOut:
    """Internal note (agent or Org Admin). Never shown to customers, never counts as a first response."""
    if user.role not in (Role.AGENT, Role.ORG_ADMIN):
        raise Forbidden("Only staff can add internal notes")
    ticket = load_visible_ticket(db, user, ticket_id)
    note = TicketMessage(ticket_id=ticket.id, sender_id=user.id, body=data.body, is_internal=True)
    db.add(note)
    db.commit()
    db.refresh(note)
    return MessageOut.from_message(note)


# ================================================================ update / assign
def update_ticket(db: Session, user: User, ticket_id: int, data: TicketUpdate) -> TicketDetailOut:
    """Change status, priority or category (agent: own tickets, Org Admin: any)."""
    if user.role not in (Role.AGENT, Role.ORG_ADMIN):
        raise Forbidden("Only staff can update tickets")
    ticket = load_visible_ticket(db, user, ticket_id)

    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        raise BusinessRuleError("Nothing to update")
    if ticket.status == TicketStatus.CLOSED:
        raise BusinessRuleError("A closed ticket cannot be changed")

    old = {"status": ticket.status.value, "priority": ticket.priority.value, "category": ticket.category.value}

    target = changes.get("status")
    if target is not None and target != ticket.status:
        if target == TicketStatus.RESOLVED:
            raise BusinessRuleError("Use POST /tickets/{id}/resolve to resolve a ticket")
        if target == TicketStatus.ESCALATED:
            raise BusinessRuleError("Use POST /tickets/{id}/escalate to escalate a ticket")
        if target not in PATCH_STATUS_TRANSITIONS.get(ticket.status, set()):
            raise BusinessRuleError(f"Cannot change status from '{ticket.status.value}' to '{target.value}'")
        if ticket.status == TicketStatus.RESOLVED and target == TicketStatus.IN_PROGRESS:
            ticket.resolved_at = None  # reopened
        ticket.status = target

    new_priority = changes.get("priority")
    if new_priority is not None and new_priority != ticket.priority:
        ticket.priority = new_priority
        if ticket.status not in FINISHED:
            # Deadlines are recalculated from the ORIGINAL creation time with the new priority's policy.
            policy = sla_service.get_policy_for_priority(db, ticket.organization_id, new_priority)
            sla_service.apply_deadlines(ticket, policy, ticket.created_at)

    if "category" in changes:
        ticket.category = changes["category"]

    new = {"status": ticket.status.value, "priority": ticket.priority.value, "category": ticket.category.value}
    _audit(db, user, "ticket.update", ticket, old, new)
    db.commit()
    return get_ticket(db, user, ticket_id)


def assign_ticket(db: Session, user: User, ticket_id: int, data: AssignRequest) -> TicketDetailOut:
    """Org Admin assigns or reassigns a ticket to an active agent of the same organization."""
    if user.role != Role.ORG_ADMIN:
        raise Forbidden("Only an Org Admin can assign tickets")
    ticket = load_visible_ticket(db, user, ticket_id)
    if ticket.status == TicketStatus.CLOSED:
        raise BusinessRuleError("A closed ticket cannot be reassigned")

    agent = db.scalar(
        select(User).where(
            User.id == data.agent_id,
            User.organization_id == ticket.organization_id,
            User.role == Role.AGENT,
            User.is_active.is_(True),
        )
    )
    if agent is None:
        raise NotFound("Agent not found in your organization")
    if ticket.assigned_agent_id == agent.id:
        return get_ticket(db, user, ticket_id)  # nothing to change

    old = {"assigned_agent_id": ticket.assigned_agent_id}
    ticket.assigned_agent_id = agent.id
    _audit(db, user, "ticket.assign", ticket, old, {"assigned_agent_id": agent.id})
    notification_service.notify(
        db, agent.id, f"Ticket #{ticket.id} assigned to you", ticket.subject,
        NotificationType.TICKET, organization_id=ticket.organization_id,
    )
    db.commit()
    return get_ticket(db, user, ticket_id)


# ================================================================ escalate / resolve
def escalate_ticket(
    db: Session, user: User, ticket_id: int, data: Optional[EscalateRequest] = None
) -> TicketDetailOut:
    """The assigned agent escalates to the Org Admins."""
    if user.role != Role.AGENT:
        raise Forbidden("Only the assigned agent can escalate a ticket")
    ticket = load_visible_ticket(db, user, ticket_id)
    if ticket.status in FINISHED:
        raise BusinessRuleError("A resolved or closed ticket cannot be escalated")
    if ticket.status == TicketStatus.ESCALATED:
        raise BusinessRuleError("This ticket is already escalated")

    old_status = ticket.status.value
    ticket.status = TicketStatus.ESCALATED

    reason = data.reason.strip() if data and data.reason else None
    if reason:
        db.add(TicketMessage(ticket_id=ticket.id, sender_id=user.id, body=f"Escalated: {reason}", is_internal=True))

    _audit(db, user, "ticket.escalate", ticket, {"status": old_status}, {"status": "escalated"})
    notification_service.notify_org_admins(
        db, ticket.organization_id, f"Ticket #{ticket.id} escalated",
        f"{user.full_name} escalated: {ticket.subject}", NotificationType.TICKET,
    )
    db.commit()
    return get_ticket(db, user, ticket_id)


def resolve_ticket(
    db: Session, user: User, ticket_id: int, data: Optional[ResolveRequest] = None
) -> TicketDetailOut:
    """Agent (own ticket) or Org Admin marks a ticket resolved. An optional note is sent to the customer."""
    if user.role not in (Role.AGENT, Role.ORG_ADMIN):
        raise Forbidden("Only staff can resolve tickets")
    ticket = load_visible_ticket(db, user, ticket_id)
    if ticket.status in FINISHED:
        raise BusinessRuleError("This ticket is already resolved or closed")

    now = utcnow()
    old_status = ticket.status.value
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = now
    if ticket.resolution_due and now > ticket.resolution_due:
        ticket.resolution_breached = True

    note = data.note.strip() if data and data.note else None
    if note:
        db.add(TicketMessage(ticket_id=ticket.id, sender_id=user.id, body=note, is_internal=False))
    _mark_first_response(ticket, now)  # resolving counts as the customer's first answer if none was sent

    _audit(db, user, "ticket.resolve", ticket, {"status": old_status}, {"status": "resolved"})
    _notify_customer(db, ticket, f"Ticket #{ticket.id} resolved", f"Your ticket was resolved: {ticket.subject}")
    db.commit()
    return get_ticket(db, user, ticket_id)
