# ----------------------------------------------------------------------
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, Unauthorized


def hash_password(plain: str) -> str:
    password = plain.encode("utf-8")
    # bcrypt only considers the first 72 bytes; reject longer passwords rather
    # than silently allowing two different passwords to produce the same hash.
    if len(password) > 72:
        raise BusinessRuleError("Password must be no longer than 72 UTF-8 bytes")
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        password = plain.encode("utf-8")
        if len(password) > 72:
            return False
        return bcrypt.checkpw(password, hashed.encode("ascii"))
    except (AttributeError, TypeError, ValueError):
        return False


def create_access_token(user_id, role, organization_id=None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": str(getattr(role, "value", role)),
               "organization_id": organization_id, "iat": now,
               "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise Unauthorized("Invalid or expired authentication token") from exc
# app/core/security.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Password hashing and JWT helpers.
# ----------------------------------------------------------------------
# TODO:
#   - hash_password(plain) -> hash
#   - verify_password(plain, hash) -> bool
#   - create_access_token(user_id, role, organization_id) -> token string
#   - decode_token(token) -> payload or raise Unauthorized
