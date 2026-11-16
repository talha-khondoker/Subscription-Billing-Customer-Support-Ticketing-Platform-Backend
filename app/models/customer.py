# ----------------------------------------------------------------------
# app/models/customer.py
# Owner:   Member 6
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'customers (org)':
#   -       user_id (unique)
#   -       phone
#   -       company_name


from typing import List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, org_fk


class Customer(Base, IdMixin, TimestampMixin):
    __tablename__ = "customers"

    organization_id: Mapped[int] = org_fk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    user: Mapped["User"] = relationship(back_populates="customer_profile")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="customer")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="customer")
    payments: Mapped[List["Payment"]] = relationship(back_populates="customer")
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="customer")
