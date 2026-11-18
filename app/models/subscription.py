# ----------------------------------------------------------------------
# app/models/subscription.py
# Owner:   Member 2
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'subscriptions (org)':
#   -       customer_id
#   -       plan_id
#   -       status
#   -       start_date
#   -       current_period_start
#   -       current_period_end
#   -       next_billing_date
#   -       paused_at
#   -       cancelled_at
#   -       cancel_at_period_end


from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import SubscriptionStatus
from app.models.base import IdMixin, TimestampMixin, enum_col, org_fk
from app.utils.dates import utcnow


class Subscription(Base, IdMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_status_next_billing", "status", "next_billing_date"),)

    organization_id: Mapped[int] = org_fk()
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True, nullable=False)
    status: Mapped[SubscriptionStatus] = enum_col(
        SubscriptionStatus, default=SubscriptionStatus.ACTIVE, nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="subscription")

