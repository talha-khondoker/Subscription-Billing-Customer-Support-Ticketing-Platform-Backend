# ----------------------------------------------------------------------
# app/utils/money.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Money helpers (Decimal only).
# ----------------------------------------------------------------------


"""Money helpers. Never use float for money."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def to_money(value) -> Decimal:
    """Convert any number to a Decimal rounded to 2 places (half up)."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
