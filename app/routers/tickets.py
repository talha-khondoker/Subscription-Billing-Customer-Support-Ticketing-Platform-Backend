# ----------------------------------------------------------------------
# app/routers/tickets.py
# Owner:   Member 5
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1

"""Ticket endpoints. Owner: Member 5. Paths are full; main.py adds /api/v1.
(Phase 2 + Phase 3 - replaces the Phase 2 file.)"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_agent, current_customer, current_org_admin, current_staff, require_roles
from app.core.enums import Role, TicketCategory, TicketPriority, TicketStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.ticket import (
    AssignRequest, BillingContextOut, EscalateRequest, MessageCreate, MessageOut, ResolveRequest,
    TicketCreate, TicketDetailOut, TicketOut, TicketUpdate,
)
from app.services import billing_context_service, ticket_service

router = APIRouter(tags=["tickets"])

any_ticket_user = require_roles(Role.CUSTOMER, Role.AGENT, Role.ORG_ADMIN)
customer_or_agent = require_roles(Role.CUSTOMER, Role.AGENT)


@router.post("/tickets", response_model=TicketDetailOut, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), user: User = Depends(current_customer)):
    return ticket_service.create_ticket(db, user, data)


@router.get("/tickets", response_model=Page[TicketOut])
def list_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    category: Optional[TicketCategory] = None,
    search: Optional[str] = Query(None, description="part of the subject"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(any_ticket_user),
):
    return ticket_service.list_tickets(db, user, status, priority, category, search, page, page_size)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(any_ticket_user)):
    return ticket_service.get_ticket(db, user, ticket_id)


@router.patch("/tickets/{ticket_id}", response_model=TicketDetailOut)
def update_ticket(
    ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db), user: User = Depends(current_staff)
):
    return ticket_service.update_ticket(db, user, ticket_id, data)


@router.post("/tickets/{ticket_id}/assign", response_model=TicketDetailOut)
def assign_ticket(
    ticket_id: int, data: AssignRequest, db: Session = Depends(get_db), user: User = Depends(current_org_admin)
):
    return ticket_service.assign_ticket(db, user, ticket_id, data)


@router.post("/tickets/{ticket_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def add_message(
    ticket_id: int, data: MessageCreate, db: Session = Depends(get_db), user: User = Depends(customer_or_agent)
):
    return ticket_service.add_message(db, user, ticket_id, data)


@router.post("/tickets/{ticket_id}/notes", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def add_internal_note(
    ticket_id: int, data: MessageCreate, db: Session = Depends(get_db), user: User = Depends(current_staff)
):
    return ticket_service.add_internal_note(db, user, ticket_id, data)


@router.post("/tickets/{ticket_id}/escalate", response_model=TicketDetailOut)
def escalate_ticket(
    ticket_id: int,
    data: Optional[EscalateRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_agent),
):
    return ticket_service.escalate_ticket(db, user, ticket_id, data)


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketDetailOut)
def resolve_ticket(
    ticket_id: int,
    data: Optional[ResolveRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_staff),
):
    return ticket_service.resolve_ticket(db, user, ticket_id, data)


@router.get("/tickets/{ticket_id}/billing-context", response_model=BillingContextOut)
def get_billing_context(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(current_staff)):
    """Billing-to-Ticket View: subscription, invoices, payments, failed attempts, refunds, past tickets."""
    return billing_context_service.get_billing_context(db, user, ticket_id)
