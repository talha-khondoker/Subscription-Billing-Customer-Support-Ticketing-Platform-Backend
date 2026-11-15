# ----------------------------------------------------------------------
# app/services/sla_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Defaults: Urgent 15 min / 4 h, High 1 h / 8 h, Medium 4 h / 24 h, Low 8 h / 72 h.
# TODO:
#   - get_policy(db, org_id, priority)
#   - apply_deadlines(ticket, policy)  -> first_response_due, resolution_due
#   - check_breaches(db)  -> flag breaches, escalate overdue tickets, notify (used by sla_job)
#   - CRUD for SLA policies
