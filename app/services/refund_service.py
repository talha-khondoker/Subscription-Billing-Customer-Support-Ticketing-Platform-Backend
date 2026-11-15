# ----------------------------------------------------------------------
# app/services/refund_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_refund(db, admin, payment, amount, reason)  -> cannot exceed paid amount minus earlier refunds
#   - full refund marks invoice and payment refunded
#   - list_refunds(db, org_id, page)
#   - always write an audit log
