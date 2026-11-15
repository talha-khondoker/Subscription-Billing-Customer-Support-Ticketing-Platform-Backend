# ----------------------------------------------------------------------
# app/models/ticket.py
# Owner:   Member 5
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'tickets (org)':
#   -       customer_id
#   -       subject
#   -       description
#   -       category
#   -       priority
#   -       status
#   -       assigned_agent_id
#   -       sla_policy_id
#   -       first_response_due
#   -       resolution_due
#   -       first_responded_at
#   -       resolved_at
#   -       first_response_breached
#   -       resolution_breached
#   - table 'ticket_messages':
#   -       ticket_id
#   -       sender_id
#   -       body
#   -       is_internal (internal note)
