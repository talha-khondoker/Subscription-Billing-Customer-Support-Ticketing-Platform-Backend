# ----------------------------------------------------------------------
# app/services/proration_service.py
# Owner:   Member 3
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - calculate_proration(old_plan, new_plan, period_start, period_end, change_date)
#   - credit = old_price x remaining_days / period_days; charge = new_price x remaining_days / period_days
