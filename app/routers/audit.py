# ----------------------------------------------------------------------
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_org_admin
from app.models.user import User
from app.services.audit_service import list_logs
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogOut])
def get_logs(entity: str | None = None, actor: int | None = None,
             date_from: datetime | None = None, date_to: datetime | None = None,
             page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
             db: Session = Depends(get_db), user: User = Depends(current_org_admin)):
    result = list_logs(db, user.organization_id,
                       {"entity": entity, "actor": actor, "date_from": date_from, "date_to": date_to},
                       page, page_size)
    return Page[AuditLogOut](**result.model_dump())
# app/routers/audit.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET /audit-logs [OA]  filters: entity, actor, date
