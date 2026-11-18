# ----------------------------------------------------------------------
# app/routers/payments.py
# Owner:   Member 4
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /invoices/{id}/pay [CU]  pay through the mock gateway
#   - GET  /payments/me [CU]
#   - GET  /payments [OA, AG]
#   - GET  /payments/{id}/attempts [CU, OA, AG]
#   - POST /payments/{id}/refund [OA]
#   - GET  /refunds [OA]
#   - PUT  /gateway/mock-config [OA]  set mock result mode

# Routes validate requests and roles, then call Member 4 service functions.
