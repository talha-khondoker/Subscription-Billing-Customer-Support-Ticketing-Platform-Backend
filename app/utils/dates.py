# ----------------------------------------------------------------------
# app/utils/dates.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Date helpers (naive UTC).
# ----------------------------------------------------------------------


"""Date helpers. All datetimes in the project are naive UTC."""
import calendar
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time without tzinfo (MySQL DATETIME does not store time zones)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def add_months(dt: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day (Jan 31 + 1 month = Feb 28/29)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def days_between(a: datetime, b: datetime) -> int:
    """Whole calendar days between two dates, independent of time-of-day."""
    return (b.date() - a.date()).days


def add_period(dt: datetime, billing_period) -> datetime:
    value = getattr(billing_period, "value", billing_period)
    if value == "monthly":
        return add_months(dt, 1)
    if value == "yearly":
        return add_months(dt, 12)
    raise ValueError(f"Unsupported billing period: {value}")
