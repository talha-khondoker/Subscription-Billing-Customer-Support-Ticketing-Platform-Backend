# ----------------------------------------------------------------------
# app/models/organization.py
# Owner:   Member 1
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'organizations':
#   -       name (unique)
#   -       status


from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import OrganizationStatus
from app.models.base import IdMixin, TimestampMixin, enum_col


class Organization(Base, IdMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    status: Mapped[OrganizationStatus] = enum_col(
        OrganizationStatus, default=OrganizationStatus.ACTIVE, nullable=False
    )

    users: Mapped[List["User"]] = relationship(back_populates="organization")
