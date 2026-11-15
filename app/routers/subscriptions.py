# ----------------------------------------------------------------------
# app/routers/subscriptions.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /subscriptions [CU]  subscribe (creates first invoice + payment)
#   - GET  /subscriptions/me [CU]
#   - GET  /subscriptions [OA, AG]  list with filters
#   - POST /subscriptions/{id}/change-plan [CU]
#   - POST /subscriptions/{id}/pause [CU]
#   - POST /subscriptions/{id}/resume [CU]
#   - POST /subscriptions/{id}/cancel [CU, OA]
