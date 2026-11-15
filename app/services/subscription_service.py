# ----------------------------------------------------------------------
# app/services/subscription_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Status flow: active <-> paused; active -> past_due after last failed retry; any -> cancelled.
# TODO:
#   - create_subscription(db, customer, plan)  -> calls invoice_service then payment_service
#   - change_plan(db, subscription, new_plan)  -> uses proration_service
#   - pause / resume
#   - cancel(db, subscription, at_period_end)
#   - renew(db, subscription)  -> advance period, create invoice (used by renewal job)
#   - mark_past_due(db, subscription)
