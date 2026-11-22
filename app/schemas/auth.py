# ----------------------------------------------------------------------
# app/schemas/auth.py
# Owner:   Member 1
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - RegisterRequest (email, password, full_name, organization_id)
#   - LoginRequest
#   - TokenResponse (access_token, token_type, user)
#   - UserOut

# ----------------------------------------------------------------------
# app/schemas/auth.py
# Owner:   Member 1
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int | None
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=150)
    organization_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
