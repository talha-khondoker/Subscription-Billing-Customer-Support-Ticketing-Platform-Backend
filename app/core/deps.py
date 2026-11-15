# ----------------------------------------------------------------------
# app/core/deps.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Reusable FastAPI dependencies for authentication and role checks.
# ----------------------------------------------------------------------
# TODO:
#   - get_current_user: read bearer token, load the user, reject inactive users and disabled organizations
#   - require_roles(*roles): dependency factory that returns 403 when the role is not allowed
#   - convenience dependencies: current_org_admin, current_agent, current_customer
