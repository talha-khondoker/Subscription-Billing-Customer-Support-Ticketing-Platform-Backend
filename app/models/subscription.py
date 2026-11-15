# ----------------------------------------------------------------------
# app/models/subscription.py
# Owner:   Member 2
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'subscriptions (org)':
#   -       customer_id
#   -       plan_id
#   -       status
#   -       start_date
#   -       current_period_start
#   -       current_period_end
#   -       next_billing_date
#   -       paused_at
#   -       cancelled_at
#   -       cancel_at_period_end
