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
