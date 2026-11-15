# ----------------------------------------------------------------------
# app/routers/tickets.py
# Owner:   Member 5
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /tickets [CU]  auto SLA deadlines + auto assignment
#   - GET   /tickets [CU, AG, OA]  CU own, AG assigned, OA all
#   - GET   /tickets/{id} [CU, AG, OA]  hide internal notes from CU
#   - PATCH /tickets/{id} [AG, OA]  status, priority, category
#   - POST  /tickets/{id}/assign [OA]
#   - POST  /tickets/{id}/messages [CU, AG]
#   - POST  /tickets/{id}/notes [AG, OA]  internal note
#   - POST  /tickets/{id}/escalate [AG]
#   - POST  /tickets/{id}/resolve [AG, OA]
#   - GET   /tickets/{id}/billing-context [AG, OA]  Billing-to-Ticket View
