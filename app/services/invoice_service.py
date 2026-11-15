# ----------------------------------------------------------------------
# app/services/invoice_service.py
# Owner:   Member 3
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - generate_for_subscription(db, subscription)  -> items, tax, discount, total, invoice number
#   - build_proration_invoice(db, subscription, amount)
#   - get_invoice(db, user, id) / list_invoices(db, user, filters, page)
#   - recalculate_totals(invoice): subtotal = sum(items); tax = (subtotal - discount) x tax%; total = subtotal - discount + tax
