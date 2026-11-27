# ----------------------------------------------------------------------
# app/models/ticket.py
# Owner:   Member 5
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.


from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import TicketCategory, TicketPriority, TicketStatus
from app.models.base import IdMixin, TimestampMixin, enum_col, org_fk


class Ticket(Base, IdMixin, TimestampMixin):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_org_status", "organization_id", "status"),
        Index("ix_tickets_agent_status", "assigned_agent_id", "status"),
    )

    organization_id: Mapped[int] = org_fk()
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[TicketCategory] = enum_col(TicketCategory, default=TicketCategory.GENERAL, nullable=False)
    priority: Mapped[TicketPriority] = enum_col(TicketPriority, default=TicketPriority.MEDIUM, nullable=False)
    status: Mapped[TicketStatus] = enum_col(TicketStatus, default=TicketStatus.OPEN, nullable=False)
    assigned_agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    sla_policy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sla_policies.id"), nullable=True)

    first_response_due: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)
    resolution_due: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)
    first_responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_response_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    assigned_agent: Mapped[Optional["User"]] = relationship()
    sla_policy: Mapped[Optional["SlaPolicy"]] = relationship()
    messages: Mapped[List["TicketMessage"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.id"
    )


class TicketMessage(Base, IdMixin, TimestampMixin):
    __tablename__ = "ticket_messages"

    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # True = internal note. Never return internal notes to customers.
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()
