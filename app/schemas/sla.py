# ----------------------------------------------------------------------
# app/schemas/sla.py
# Owner:   Member 5
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - SlaPolicyCreate
#   - SlaPolicyUpdate
#   - SlaPolicyOut
"""SLA policy schemas. Owner: Member 5."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import TicketPriority


class SlaPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: TicketPriority
    first_response_minutes: int = Field(gt=0, le=60 * 24 * 30)
    resolution_minutes: int = Field(gt=0, le=60 * 24 * 365)
    is_active: bool = True

    @model_validator(mode="after")
    def resolution_not_shorter_than_first_response(self):
        if self.resolution_minutes < self.first_response_minutes:
            raise ValueError("resolution_minutes must be >= first_response_minutes")
        return self


class SlaPolicyUpdate(BaseModel):
    """Only the fields that are sent are changed. The priority of a policy cannot change."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    first_response_minutes: Optional[int] = Field(default=None, gt=0, le=60 * 24 * 30)
    resolution_minutes: Optional[int] = Field(default=None, gt=0, le=60 * 24 * 365)
    is_active: Optional[bool] = None


class SlaPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    priority: TicketPriority
    first_response_minutes: int
    resolution_minutes: int
    is_active: bool
    created_at: datetime
