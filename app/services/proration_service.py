
# Purpose: Business rules. Works with the DB session and models.
#          Called by routers and jobs.
# ----------------------------------------------------------------------*

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def calculate_proration(
    old_plan,
    new_plan,
    period_start,
    period_end,
    change_date
):
    """
    Calculate the credit from the old plan and charge for the new plan.

    Returns:
        old_credit: Unused amount from the old plan.
        new_charge: Remaining amount for the new plan.
        net_amount: Final amount to charge or credit.
    """

    # Validate dates
    if period_end <= period_start:
        raise ValueError("Period end must be after period start.")

    if change_date < period_start or change_date > period_end:
        raise ValueError("Change date must be within the billing period.")

    # Get plan prices
    old_price = Decimal(str(old_plan.price))
    new_price = Decimal(str(new_plan.price))

    if old_price < 0 or new_price < 0:
        raise ValueError("Plan price cannot be negative.")

    # Calculate total billing days
    total_days = Decimal(str((period_end - period_start).days))

    # Calculate remaining days
    remaining_days = Decimal(str((period_end - change_date).days))

    # Calculate unused credit from old plan
    old_credit = (
        old_price * remaining_days / total_days
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate charge for new plan
    new_charge = (
        new_price * remaining_days / total_days
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate final amount
    net_amount = new_charge - old_credit

    return {
        "old_credit": old_credit,
        "new_charge": new_charge,
        "net_amount": net_amount
    }
