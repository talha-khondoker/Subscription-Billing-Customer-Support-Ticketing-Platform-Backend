# ----------------------------------------------------------------------
# app/core/tenancy.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Organization (tenant) isolation helper.
# ----------------------------------------------------------------------
from app.core.enums import Role
from app.core.exceptions import NotFound


def scoped(query, model, user, *, allow_super_admin=False):
    """Restrict organization-owned model queries to the authenticated tenant."""
    org_column = getattr(model, "organization_id", None)
    if org_column is None:
        return query
    if str(user.role) == Role.SUPER_ADMIN.value and allow_super_admin:
        return query
    if user.organization_id is None:
        return query.filter(org_column.is_(None))
    return query.filter(org_column == user.organization_id)


def get_owned_or_404(db, model, id, user, *, allow_super_admin=False):
    item = db.get(model, id)
    if item is None:
        raise NotFound()
    org_id = getattr(item, "organization_id", None)
    if str(user.role) == Role.SUPER_ADMIN.value and allow_super_admin:
        return item
    if org_id != user.organization_id:
        raise NotFound()
    return item
