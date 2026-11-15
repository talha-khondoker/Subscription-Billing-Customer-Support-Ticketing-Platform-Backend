# ----------------------------------------------------------------------
# app/models/user.py
# Owner:   Member 1
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'users':
#   -       organization_id (null for Super Admin)
#   -       email (unique)
#   -       password_hash
#   -       full_name
#   -       role
#   -       is_active
