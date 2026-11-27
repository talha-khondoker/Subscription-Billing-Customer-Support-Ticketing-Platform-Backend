# ----------------------------------------------------------------------
# app/schemas/plan.py
# Owner:   Member 2
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------


from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.core.enums import BillingPeriod


# Create Plan
class PlanCreate(BaseModel):

    name: str = Field(..., min_length=2, max_length=100)

    description: Optional[str] = None

    price: Decimal = Field(..., ge=0)

    billing_period: BillingPeriod

    tax_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=100
    )


# Update Plan
class PlanUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: Optional[str] = None

    price: Optional[Decimal] = Field(
        default=None,
        ge=0
    )

    billing_period: Optional[BillingPeriod] = None

    tax_percent: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=100)

    is_active: Optional[bool] = None


# Response Schema
class PlanOut(BaseModel):

    id: int
    organization_id: int
    name: str
    description: Optional[str]
    price: Decimal
    billing_period: BillingPeriod
    tax_percent: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
