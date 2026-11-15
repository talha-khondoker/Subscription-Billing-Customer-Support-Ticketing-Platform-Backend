# ----------------------------------------------------------------------
# app/routers/admin_jobs.py
# Owner:   Member 4
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /admin/jobs/run-renewals [OA]  manual trigger (demo)
#   - POST /admin/jobs/run-retries [OA]  manual trigger (demo)
#   - POST /admin/jobs/run-sla-check [OA]  manual trigger (demo)
