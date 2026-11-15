# ----------------------------------------------------------------------
# app/core/security.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Password hashing and JWT helpers.
# ----------------------------------------------------------------------
# TODO:
#   - hash_password(plain) -> hash
#   - verify_password(plain, hash) -> bool
#   - create_access_token(user_id, role, organization_id) -> token string
#   - decode_token(token) -> payload or raise Unauthorized
