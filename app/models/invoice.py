# ----------------------------------------------------------------------
# app/models/invoice.py
# Owner:   Member 3
# Purpose: SQLAlchemy model(s). Columns only, no business logic.
# ----------------------------------------------------------------------
# Notes:
#   Every table also has: id, created_at, updated_at (except invoice_items, payment_attempts).
#   Tables marked (org) also have organization_id (indexed).
#   Money = Decimal(12,2). Enums are stored as text. All datetimes are naive UTC.
# TODO:
#   - table 'invoices (org)':
#   -       customer_id
#   -       subscription_id
#   -       invoice_number (unique per org)
#   -       period_start
#   -       period_end
#   -       subtotal
#   -       discount_amount
#   -       tax_amount
#   -       total
#   -       status
#   -       due_date
#   -       issued_at
#   -       paid_at
#   - table 'invoice_items':
#   -       invoice_id
#   -       item_type
#   -       description
#   -       quantity
#   -       unit_amount
#   -       amount (may be negative)
