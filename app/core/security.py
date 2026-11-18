# ----------------------------------------------------------------------
# app/core/security.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Password hashing and JWT helpers.
# ----------------------------------------------------------------------
# TODO:
#   - hash_password(plain) -> hash
#   - verify_password(plain, hash) -> bool
#   - create_access_token(user_id, role, organization_id) -> token string
#   - decode_token(token) -> payload or raise Unauthorized


"""Password hashing and JWT helpers. Owner: Member 1.

Needs:  pip install bcrypt "python-jose[cryptography]"
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import Unauthorized

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    # bcrypt only uses the first 72 bytes of a password.
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, role, organization_id: Optional[int]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": getattr(role, "value", str(role)),
        "org": organization_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise Unauthorized("Invalid or expired token")
