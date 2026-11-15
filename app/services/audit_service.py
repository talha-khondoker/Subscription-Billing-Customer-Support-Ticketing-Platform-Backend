# ----------------------------------------------------------------------
# app/services/audit_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Must be called for: plan change, invoice change, refund, ticket reassignment, subscription cancellation.
# TODO:
#   - log(db, actor, action, entity_type, entity_id, old, new)
#   - list_logs(db, org_id, filters, page)
