# ----------------------------------------------------------------------
# app/models/plan.py
# Owner:   Member 2
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.



from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import BillingPeriod
from app.models.base import IdMixin, TimestampMixin, enum_col, money, org_fk


class Plan(Base, IdMixin, TimestampMixin):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_plans_org_name"),)

    organization_id: Mapped[int] = org_fk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = money()
    billing_period: Mapped[BillingPeriod] = enum_col(BillingPeriod, nullable=False)
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")
