# ----------------------------------------------------------------------
# app/models/__init__.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Import every model so Base.metadata knows all tables.
# ----------------------------------------------------------------------
# TODO:
#   - import all model classes listed above (needed for create_all and Alembic)

"""Import every model here so Base.metadata knows all tables (needed for create_all and Alembic)."""
from app.models.organization import Organization
from app.models.user import User
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceItem
from app.models.payment import Payment, PaymentAttempt, Refund
from app.models.sla_policy import SlaPolicy
from app.models.ticket import Ticket, TicketMessage
from app.models.notification import Notification
from app.models.audit_log import AuditLog

__all__ = [
    "Organization", "User", "Customer", "Plan", "Subscription", "Invoice", "InvoiceItem",
    "Payment", "PaymentAttempt", "Refund", "SlaPolicy", "Ticket", "TicketMessage",
    "Notification", "AuditLog",
]
