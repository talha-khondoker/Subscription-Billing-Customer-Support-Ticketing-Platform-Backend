# ----------------------------------------------------------------------
# app/routers/users.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /users/agents [OA]  create agent
#   - GET   /users/agents [OA]  list agents
#   - PATCH /users/{id} [OA]  update or deactivate
