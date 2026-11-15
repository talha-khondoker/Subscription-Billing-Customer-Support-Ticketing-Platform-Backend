# ----------------------------------------------------------------------
# app/models/plan.py
# Owner:   Member 2
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'plans (org)':
#   -       name (unique per org)
#   -       description
#   -       price
#   -       billing_period
#   -       tax_percent
#   -       is_active
