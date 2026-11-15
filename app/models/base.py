# ----------------------------------------------------------------------
# app/models/base.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'mixins and helpers':
#   -       IdMixin
#   -       TimestampMixin
#   -       org_fk()
#   -       money()
#   -       enum_col()
