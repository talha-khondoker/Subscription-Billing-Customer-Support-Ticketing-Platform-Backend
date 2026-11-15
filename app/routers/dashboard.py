# ----------------------------------------------------------------------
# app/routers/dashboard.py
# Owner:   Member 6
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET /dashboard/platform [SA]
#   - GET /dashboard/admin [OA]
#   - GET /dashboard/agent [AG]
#   - GET /dashboard/customer [CU]
