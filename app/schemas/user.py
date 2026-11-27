# ----------------------------------------------------------------------
# app/schemas/user.py
# Owner:   Member 1
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.core.enums import Role


class AgentCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int | None
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
