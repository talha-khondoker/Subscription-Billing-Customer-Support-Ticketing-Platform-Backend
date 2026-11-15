# ----------------------------------------------------------------------
# app/core/exceptions.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Custom errors and one consistent error response format.
# ----------------------------------------------------------------------
# TODO:
#   - AppError base class (status_code, detail, code)
#   - NotFound (404), Forbidden (403), Unauthorized (401), BusinessRuleError (400/409)
#   - register_exception_handlers(app): return {"detail": "...", "code": "..."}
