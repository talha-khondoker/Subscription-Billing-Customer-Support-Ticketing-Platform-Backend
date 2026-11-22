# ----------------------------------------------------------------------
# app/routers/invoices.py
# Owner:   Member 3
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET /invoices/me [CU]
#   - GET /invoices [OA, AG]  filters: customer, status, date
#   - GET /invoices/{id} [CU, OA, AG]  with items
