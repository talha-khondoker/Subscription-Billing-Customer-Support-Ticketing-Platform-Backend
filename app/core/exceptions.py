# ----------------------------------------------------------------------
# app/core/exceptions.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Custom errors and one consistent error response format.
# ----------------------------------------------------------------------


"""Custom errors and one consistent error format. Owner: Member 1.

Usage in services:   raise NotFound("Ticket not found")
Response format:     {"detail": "Ticket not found", "code": "not_found"}
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code: int = 400
    code: str = "app_error"
    default_detail: str = "Application error"

    def __init__(self, detail: str | None = None, code: str | None = None):
        self.detail = detail or self.default_detail
        if code:
            self.code = code
        super().__init__(self.detail)


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"
    default_detail = "Not authenticated"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    default_detail = "You do not have permission for this action"


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    default_detail = "Resource not found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    default_detail = "Conflict with the current state"


class BusinessRuleError(AppError):
    """A request that is valid but breaks a business rule (e.g. refund above paid amount)."""
    status_code = 400
    code = "business_rule_violation"
    default_detail = "Business rule violated"

    def __init__(self, detail: str | None = None, status_code: int | None = None, code: str | None = None):
        # Services call BusinessRuleError("msg", 409, "CODE"); keyword use (detail=..., code=...) also works.
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": "http_error"},
            headers=getattr(exc, "headers", None),
        )
    # Validation errors (422) keep FastAPI's default format, which Swagger shows clearly.
