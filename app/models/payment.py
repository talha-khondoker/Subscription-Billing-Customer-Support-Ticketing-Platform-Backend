# ----------------------------------------------------------------------
# app/models/payment.py
# Owner:   Member 4
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'payments (org)':
#   -       invoice_id
#   -       customer_id
#   -       amount
#   -       status
#   -       gateway_reference
#   -       failure_reason
#   - table 'payment_attempts':
#   -       payment_id
#   -       invoice_id
#   -       attempt_number
#   -       status
#   -       gateway_response (JSON)
#   -       attempted_at
#   -       next_retry_at (indexed)
#   - table 'refunds (org)':
#   -       payment_id
#   -       invoice_id
#   -       amount
#   -       reason
#   -       issued_by (user)
#   -       status



from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import AttemptStatus, PaymentStatus, RefundStatus
from app.models.base import IdMixin, TimestampMixin, enum_col, money, org_fk
from app.utils.dates import utcnow


class Payment(Base, IdMixin, TimestampMixin):
    __tablename__ = "payments"

    organization_id: Mapped[int] = org_fk()
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    amount: Mapped[Decimal] = money()
    status: Mapped[PaymentStatus] = enum_col(PaymentStatus, default=PaymentStatus.PENDING, nullable=False)
    gateway_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")
    customer: Mapped["Customer"] = relationship(back_populates="payments")
    attempts: Mapped[List["PaymentAttempt"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", order_by="PaymentAttempt.attempt_number"
    )
    refunds: Mapped[List["Refund"]] = relationship(back_populates="payment")


class PaymentAttempt(Base, IdMixin):
    __tablename__ = "payment_attempts"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = enum_col(AttemptStatus, nullable=False)
    gateway_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    # Set when the attempt failed and another retry is scheduled. The retry job queries this column.
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)

    payment: Mapped["Payment"] = relationship(back_populates="attempts")


class Refund(Base, IdMixin, TimestampMixin):
    __tablename__ = "refunds"

    organization_id: Mapped[int] = org_fk()
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    amount: Mapped[Decimal] = money()
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[RefundStatus] = enum_col(RefundStatus, default=RefundStatus.COMPLETED, nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="refunds")
    issuer: Mapped["User"] = relationship()

