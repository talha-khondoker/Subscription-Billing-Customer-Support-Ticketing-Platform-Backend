# ----------------------------------------------------------------------
# app/core/tenancy.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Organization (tenant) isolation helper.
# ----------------------------------------------------------------------
# TODO:
#   - scoped(query, model, user): add organization_id filter for every org-owned table
#   - get_owned_or_404(db, model, id, user): fetch one row inside the user's organization or raise NotFound
#   - Super Admin bypasses the filter only where explicitly allowed
