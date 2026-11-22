# ----------------------------------------------------------------------
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.core.enums import OrganizationStatus


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str = Field(min_length=1, max_length=150)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    status: OrganizationStatus | None = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: OrganizationStatus
# app/schemas/organization.py
# Owner:   Member 1
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - OrganizationCreate (name + first Org Admin email/password/name)
#   - OrganizationUpdate
#   - OrganizationOut
