# ----------------------------------------------------------------------
# app/routers/plans.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /plans [OA]  create
#   - GET   /plans [OA, AG, CU]  list (customers see active only)
#   - PATCH /plans/{id} [OA]  edit or activate/deactivate
