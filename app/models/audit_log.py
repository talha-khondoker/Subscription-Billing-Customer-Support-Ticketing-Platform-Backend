# ----------------------------------------------------------------------
# app/models/audit_log.py
# Owner:   Member 1
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.

from typing import Optional

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, org_fk


class AuditLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_entity", "organization_id", "entity_type", "entity_id"),)

    # NULL for platform-level actions by the Super Admin.
    organization_id: Mapped[Optional[int]] = org_fk(nullable=True)
    # NULL when the system itself did it (scheduled jobs).
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "subscription.change_plan"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "subscription"
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    actor: Mapped[Optional["User"]] = relationship()

    @property
    def actor_name(self) -> Optional[str]:
        return self.actor.full_name if self.actor is not None else None
