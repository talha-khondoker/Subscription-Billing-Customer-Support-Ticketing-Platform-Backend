# ----------------------------------------------------------------------
# app/core/enums.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: All role and status values in one place (shared with the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - Role: super_admin, org_admin, agent, customer
#   - OrganizationStatus: active, disabled
#   - BillingPeriod: monthly, yearly
#   - SubscriptionStatus: active, paused, past_due, cancelled
#   - InvoiceStatus: open, paid, failed, void, refunded
#   - InvoiceItemType: plan, proration, discount
#   - PaymentStatus: pending, succeeded, failed, refunded
#   - AttemptStatus: succeeded, failed
#   - RefundStatus: pending, completed
#   - TicketStatus: open, in_progress, waiting_customer, escalated, resolved, closed
#   - TicketPriority: low, medium, high, urgent
#   - TicketCategory: billing, payment, technical, account, general
#   - NotificationType: info, billing, payment, ticket, sla


"""All role and status values in one place. The frontend must use these exact strings."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    AGENT = "agent"
    CUSTOMER = "customer"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class BillingPeriod(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"
    FAILED = "failed"
    VOID = "void"
    REFUNDED = "refunded"


class InvoiceItemType(StrEnum):
    PLAN = "plan"
    PRORATION = "proration"
    DISCOUNT = "discount"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class AttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RefundStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(StrEnum):
    BILLING = "billing"
    PAYMENT = "payment"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL = "general"


class NotificationType(StrEnum):
    INFO = "info"
    BILLING = "billing"
    PAYMENT = "payment"
    TICKET = "ticket"
    SLA = "sla"
