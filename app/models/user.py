# ----------------------------------------------------------------------
# app/models/user.py
# Owner:   Member 1
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'users':
#   -       organization_id (null for Super Admin)
#   -       email (unique)
#   -       password_hash
#   -       full_name
#   -       role
#   -       is_active



from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Role
from app.models.base import IdMixin, TimestampMixin, enum_col


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    # NULL for the Super Admin, who does not belong to an organization.
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[Role] = enum_col(Role, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")
    customer_profile: Mapped[Optional["Customer"]] = relationship(back_populates="user", uselist=False)
