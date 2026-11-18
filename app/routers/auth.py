# ----------------------------------------------------------------------
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from urllib.parse import parse_qs
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_customer(db, data)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={"requestBody": {"required": True, "content": {
        "application/json": {"schema": {"type": "object", "properties": {
            "email": {"type": "string", "format": "email"},
            "password": {"type": "string"}}, "required": ["email", "password"]}},
        "application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {
            "username": {"type": "string", "description": "Email address"},
            "password": {"type": "string"}}, "required": ["username", "password"]}}
    }}}
)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/x-www-form-urlencoded":
        fields = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
        payload = {
            "email": (fields.get("username") or fields.get("email") or [""])[0],
            "password": (fields.get("password") or [""])[0],
        }
    elif content_type == "application/json":
        try:
            payload = await request.json()
        except ValueError as exc:
            raise RequestValidationError([{"type": "json_invalid", "loc": ("body",),
                                          "msg": "JSON decode error", "input": None,
                                          "ctx": {"error": str(exc)}}]) from exc
    else:
        payload = {}
    try:
        data = LoginRequest.model_validate(payload)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    return auth_service.build_token_response(auth_service.authenticate(db, data.email, data.password))


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user
# app/routers/auth.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /auth/register [public]  customer self-registration
#   - POST /auth/login [public]  returns JWT
#   - GET  /auth/me [all]  current user
