# ----------------------------------------------------------------------
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, code: str = "APP_ERROR"):
        self.status_code, self.detail, self.code = status_code, detail, code
        super().__init__(detail)


class NotFound(AppError):
    def __init__(self, detail="Resource not found"):
        super().__init__(404, detail, "NOT_FOUND")


class Forbidden(AppError):
    def __init__(self, detail="Forbidden"):
        super().__init__(403, detail, "FORBIDDEN")


class Unauthorized(AppError):
    def __init__(self, detail="Authentication required"):
        super().__init__(401, detail, "UNAUTHORIZED")


class BusinessRuleError(AppError):
    def __init__(self, detail, status_code=400, code="BUSINESS_RULE_ERROR"):
        super().__init__(status_code, detail, code)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})
# app/core/exceptions.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Custom errors and one consistent error response format.
# ----------------------------------------------------------------------
# TODO:
#   - AppError base class (status_code, detail, code)
#   - NotFound (404), Forbidden (403), Unauthorized (401), BusinessRuleError (400/409)
#   - register_exception_handlers(app): return {"detail": "...", "code": "..."}
