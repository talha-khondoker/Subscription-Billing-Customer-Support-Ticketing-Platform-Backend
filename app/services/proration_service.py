# ----------------------------------------------------------------------
# app/services/proration_service.py
# Owner:   Member 3
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
"""Plan-change proration.

    credit = old_price x remaining_days / period_days
    charge = new_price x remaining_days / period_days
    net    = charge - credit      (> 0: customer pays, < 0: customer gets a credit)
"""
from datetime import datetime
from decimal import Decimal

from app.utils.dates import days_between
from app.utils.money import to_money


def calculate_proration(old_plan, new_plan, period_start: datetime, period_end: datetime,
                        change_date: datetime) -> dict:
    period_days = max(days_between(period_start, period_end), 1)
    remaining_days = min(max(days_between(change_date, period_end), 0), period_days)
    ratio = Decimal(remaining_days) / Decimal(period_days)

    credit = to_money(Decimal(str(old_plan.price)) * ratio)
    charge = to_money(Decimal(str(new_plan.price)) * ratio)
    return {
        "credit": credit,
        "charge": charge,
        "net": to_money(charge - credit),
        "remaining_days": remaining_days,
        "period_days": period_days,
    }
