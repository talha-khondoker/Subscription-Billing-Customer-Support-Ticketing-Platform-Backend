# ----------------------------------------------------------------------
# app/routers/organizations.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /organizations [SA]  create organization + first Org Admin
#   - GET   /organizations [SA]  list
#   - PATCH /organizations/{id} [SA]  edit name / enable / disable
