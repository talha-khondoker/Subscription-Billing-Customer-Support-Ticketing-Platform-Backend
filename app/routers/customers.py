# ----------------------------------------------------------------------
# app/routers/customers.py
# Owner:   Member 6
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET   /customers/me [CU]
#   - PATCH /customers/me [CU]
#   - GET   /customers [OA, AG]  with search
#   - GET   /customers/{id} [OA, AG]  profile + histories
