# ----------------------------------------------------------------------
# app/services/audit_service.py
# Owner:   Member 1
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Must be called for: plan change, invoice change, refund, ticket reassignment, subscription cancellation.
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.models.audit_log import AuditLog
from app.utils.pagination import paginate


def log(db: Session, actor, action, entity_type, entity_id, old=None, new=None):
    organization_id = getattr(actor, "organization_id", None) if actor is not None else None
    record = AuditLog(organization_id=organization_id, actor_id=getattr(actor, "id", None),
                      action=action, entity_type=entity_type, entity_id=entity_id,
                      old_values=old, new_values=new)
    db.add(record)
    db.flush()
    return record


def list_logs(db: Session, org_id, filters=None, page=1, page_size=10):
    filters = filters or {}
    query = db.query(AuditLog)
    if org_id is not None:
        query = query.filter(AuditLog.organization_id == org_id)
    if filters.get("entity"):
        query = query.filter(AuditLog.entity_type == filters["entity"])
    if filters.get("actor") is not None:
        query = query.filter(AuditLog.actor_id == filters["actor"])
    if filters.get("date_from"):
        query = query.filter(AuditLog.created_at >= filters["date_from"])
    if filters.get("date_to"):
        query = query.filter(AuditLog.created_at <= filters["date_to"])
    return paginate(query.order_by(AuditLog.created_at.desc()), page, page_size)
