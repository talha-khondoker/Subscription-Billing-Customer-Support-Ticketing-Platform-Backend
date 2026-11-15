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
