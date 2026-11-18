# ----------------------------------------------------------------------
# app/models/base.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'mixins and helpers':
#   -       IdMixin
#   -       TimestampMixin
#   -       org_fk()
#   -       money()
#   -       enum_col()


"""Shared column mixins and helpers used by every model."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.dates import utcnow


class IdMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


def org_fk(nullable: bool = False):
    """organization_id column. Add it to every table that holds organization data."""
    return mapped_column(ForeignKey("organizations.id"), index=True, nullable=nullable)


def money(**kwargs):
    """Decimal(12, 2) column, default 0.00."""
    kwargs.setdefault("default", Decimal("0.00"))
    kwargs.setdefault("nullable", False)
    return mapped_column(Numeric(12, 2), **kwargs)


def enum_col(enum_cls, **kwargs):
    """Enum stored as a VARCHAR holding the enum value (no native DB enum, easier migrations)."""
    return mapped_column(
        SAEnum(
            enum_cls,
            native_enum=False,
            length=30,
            values_callable=lambda e: [member.value for member in e],
            validate_strings=True,
        ),
        **kwargs,
    )
