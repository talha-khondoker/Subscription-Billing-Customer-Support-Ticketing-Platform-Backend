# ----------------------------------------------------------------------
# app/models/sla_policy.py
# Owner:   Member 5
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'sla_policies (org)':
#   -       name
#   -       priority (unique per org)
#   -       first_response_minutes
#   -       resolution_minutes
#   -       is_active
