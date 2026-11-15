# ----------------------------------------------------------------------
# app/models/audit_log.py
# Owner:   Member 1
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'audit_logs (org, nullable)':
#   -       actor_id (null = system)
#   -       action
#   -       entity_type
#   -       entity_id
#   -       old_values (JSON)
#   -       new_values (JSON)
