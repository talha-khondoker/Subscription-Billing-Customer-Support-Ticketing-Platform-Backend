# ----------------------------------------------------------------------
# app/models/invoice.py
# Owner:   Member 3
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.


from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import InvoiceItemType, InvoiceStatus
from app.models.base import IdMixin, TimestampMixin, enum_col, money, org_fk
from app.utils.dates import utcnow


class Invoice(Base, IdMixin, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("organization_id", "invoice_number", name="uq_invoices_org_number"),
        Index("ix_invoices_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[int] = org_fk()
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    subscription_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subscriptions.id"), index=True, nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subtotal: Mapped[Decimal] = money()
    discount_amount: Mapped[Decimal] = money()
    tax_amount: Mapped[Decimal] = money()
    total: Mapped[Decimal] = money()
    status: Mapped[InvoiceStatus] = enum_col(InvoiceStatus, default=InvoiceStatus.OPEN, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    subscription: Mapped[Optional["Subscription"]] = relationship(back_populates="invoices")
    items: Mapped[List["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.id"
    )
    payments: Mapped[List["Payment"]] = relationship(back_populates="invoice")


class InvoiceItem(Base, IdMixin):
    __tablename__ = "invoice_items"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    item_type: Mapped[InvoiceItemType] = enum_col(InvoiceItemType, default=InvoiceItemType.PLAN, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_amount: Mapped[Decimal] = money()
    amount: Mapped[Decimal] = money()  # may be negative (discount, proration credit)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
