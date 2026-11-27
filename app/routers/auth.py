# ----------------------------------------------------------------------
# app/routers/auth.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1

from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    OrganizationRegisterRequest, PasswordChange, ProfileUpdate, RegisterRequest, TokenResponse, UserOut,
)
from app.schemas.common import Message
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


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Swagger UI Authorize বাটন এবং ফর্ম লগইনের জন্য। এখানে username ফিল্ডে email দিতে হবে।"""
    user = auth_service.authenticate(db, email=form_data.username, password=form_data.password)
    return auth_service.build_token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.post("/register-organization", response_model=UserOut, status_code=201)
def register_organization(data: OrganizationRegisterRequest, db: Session = Depends(get_db)):
    """Public: a new organization signs up together with its first Org Admin."""
    try:
        user = auth_service.register_organization(db, data)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileUpdate, user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    try:
        auth_service.update_profile(db, user, data)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


@router.post("/change-password", response_model=Message)
def change_password(data: PasswordChange, user: Annotated[User, Depends(get_current_user)],
                    db: Session = Depends(get_db)):
    try:
        auth_service.change_password(db, user, data.current_password, data.new_password)
        db.commit()
        return {"message": "Password changed"}
    except Exception:
        db.rollback()
        raise
