# ----------------------------------------------------------------------
# app/services/mock_gateway.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - charge(amount, customer) -> success/failure + response dict
#   - set_mode(always_success | always_fail | random)

from decimal import Decimal
from random import choice
from typing import Any
from uuid import uuid4

from fastapi import HTTPException


MODES = ("always_success", "always_fail", "random")
current_mode = "always_success"


def set_mode(mode: str) -> str:
    """Choose how the mock gateway should respond."""

    global current_mode
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"Unsupported gateway mode: {mode}")
    current_mode = mode
    return current_mode


def charge(amount: Decimal, customer: Any = None) -> dict[str, Any]:
    """Return a fake success or failure response."""

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    success = current_mode == "always_success"
    if current_mode == "random":
        success = choice([True, False])

    return {
        "success": success,
        "gateway_reference": f"mock_{uuid4().hex}" if success else None,
        "message": "Payment approved" if success else "Payment declined",
    }
