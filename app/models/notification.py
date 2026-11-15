# ----------------------------------------------------------------------
# app/models/notification.py
# Owner:   Member 6
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'notifications (org)':
#   -       user_id
#   -       title
#   -       message
#   -       type
#   -       is_read
