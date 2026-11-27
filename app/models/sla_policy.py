# ----------------------------------------------------------------------
# app/models/sla_policy.py
# Owner:   Member 5
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.


from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import TicketPriority
from app.models.base import IdMixin, TimestampMixin, enum_col, org_fk


class SlaPolicy(Base, IdMixin, TimestampMixin):
    __tablename__ = "sla_policies"
    # One policy per priority per organization.
    __table_args__ = (UniqueConstraint("organization_id", "priority", name="uq_sla_org_priority"),)

    organization_id: Mapped[int] = org_fk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[TicketPriority] = enum_col(TicketPriority, nullable=False)
    first_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
