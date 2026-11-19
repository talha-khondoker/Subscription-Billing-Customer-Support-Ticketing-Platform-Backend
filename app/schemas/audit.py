# ----------------------------------------------------------------------
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int | None
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    old_values: dict | None
    new_values: dict | None
    created_at: datetime


class AuditLogFilter(BaseModel):
    entity: str | None = None
    actor: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
# app/schemas/audit.py
# Owner:   Member 1
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - AuditLogOut
#   - AuditLogFilter
