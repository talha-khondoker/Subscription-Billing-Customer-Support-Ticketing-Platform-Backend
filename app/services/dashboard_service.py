# ----------------------------------------------------------------------
# app/services/dashboard_service.py
# Owner:   Member 6
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - platform_dashboard(db)
#   - admin_dashboard(db, org_id)  -> MRR, ARR, active subs, churn rate, failed payments, open tickets, SLA performance
#   - agent_dashboard(db, agent)
#   - customer_dashboard(db, customer)
#   - MRR = sum of monthly-normalized prices of active subscriptions; ARR = MRR x 12; churn = cancellations in period / active at period start
