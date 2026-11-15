# ----------------------------------------------------------------------
# app/routers/auth.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /auth/register [public]  customer self-registration
#   - POST /auth/login [public]  returns JWT
#   - GET  /auth/me [all]  current user
