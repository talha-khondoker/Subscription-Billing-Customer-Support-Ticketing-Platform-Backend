
# ----------------------------------------------------------------------
# app/routers/subscriptions.py
# Owner:   Member 2
# Purpose: HTTP layer only: validate input, check role, call a service,
#          return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer.
#   Prefix: /api/v1
#
# TODO:

#   - POST /subscriptions [CU]  subscribe (creates first invoice + payment)
#   - GET  /subscriptions/me [CU]
#   - GET  /subscriptions [OA, AG]  list with filters
#   - POST /subscriptions/{id}/change-plan [CU]
#   - POST /subscriptions/{id}/pause [CU]
#   - POST /subscriptions/{id}/resume [CU]
#   - POST /subscriptions/{id}/cancel [CU, OA]

# ----------------------------------------------------------------------
# app/routers/subscriptions.py
# Owner: Member 2
# Purpose: Subscription API routes
# ----------------------------------------------------------------------

from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.deps import require_roles

from app.models.customer import Customer
from app.models.subscription import Subscription

from app.schemas.subscription import (
    SubscriptionCreate,
    ChangePlanRequest,
    CancelRequest,
    SubscriptionOut,
)

from app.services.subscription_service import (
    create_subscription,
    change_plan,
    pause_subscription,
    resume_subscription,
    cancel_subscription,
    cancel_subscription_by_admin,
    get_subscriptions,
)


router = APIRouter(
    prefix="/api/v1/subscriptions",
    tags=["Subscriptions"]
)

db_dependency = Annotated[Session, Depends(get_db)]


# ----------------------------------------------------------------------
# Helper: Get Current Customer
# ----------------------------------------------------------------------

def get_current_customer(db: Session, current_user):

    customer = db.query(Customer).filter(
        Customer.user_id == current_user.id,
        Customer.organization_id == current_user.organization_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )

    return customer


# ----------------------------------------------------------------------
# 1. Create Subscription [CUSTOMER]
# ----------------------------------------------------------------------

@router.post(
    "",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED
)
def create_subscription_api(
    data: SubscriptionCreate,
    db: db_dependency,
    current_user=Depends(require_roles(Role.CUSTOMER))
):

    customer = get_current_customer(db, current_user)

    return create_subscription(
        db=db,
        customer_id=customer.id,
        plan_id=data.plan_id
    )


# ----------------------------------------------------------------------
# 2. Get My Subscriptions [CUSTOMER]
# ----------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[SubscriptionOut]
)
def get_my_subscriptions(
    db: db_dependency,
    current_user=Depends(require_roles(Role.CUSTOMER))
):

    customer = get_current_customer(db, current_user)

    return db.query(Subscription).filter(
        Subscription.customer_id == customer.id,
        Subscription.organization_id == customer.organization_id
    ).all()


# ----------------------------------------------------------------------
# 3. Get All Subscriptions [ORG_ADMIN, AGENT]
# ----------------------------------------------------------------------

@router.get(
    "",
    response_model=list[SubscriptionOut]
)
def get_all_subscriptions(
    db: db_dependency,
    current_user=Depends(
        require_roles(Role.ORG_ADMIN, Role.AGENT)
    ),
    subscription_status: str | None = None,
    plan_id: int | None = None
):

    query = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    )

    if subscription_status is not None:
        query = query.filter(
            Subscription.status == subscription_status
        )

    if plan_id is not None:
        query = query.filter(
            Subscription.plan_id == plan_id
        )

    return query.all()


# ----------------------------------------------------------------------
# 4. Change Plan [CUSTOMER]
# ----------------------------------------------------------------------

@router.post(
    "/{subscription_id}/change-plan",
    response_model=SubscriptionOut
)
def change_subscription_plan(
    subscription_id: int,
    data: ChangePlanRequest,
    db: db_dependency,
    current_user=Depends(require_roles(Role.CUSTOMER))
):

    customer = get_current_customer(db, current_user)

    return change_plan(
        db=db,
        subscription_id=subscription_id,
        new_plan_id=data.new_plan_id,
        customer_id=customer.id
    )


# ----------------------------------------------------------------------
# 5. Pause Subscription [CUSTOMER]
# ----------------------------------------------------------------------

@router.post(
    "/{subscription_id}/pause",
    response_model=SubscriptionOut
)
def pause_subscription_api(
    subscription_id: int,
    db: db_dependency,
    current_user=Depends(require_roles(Role.CUSTOMER))
):

    customer = get_current_customer(db, current_user)

    return pause_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer.id
    )


# ----------------------------------------------------------------------
# 6. Resume Subscription [CUSTOMER]
# ----------------------------------------------------------------------

@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionOut
)
def resume_subscription_api(
    subscription_id: int,
    db: db_dependency,
    current_user=Depends(require_roles(Role.CUSTOMER))
):

    customer = get_current_customer(db, current_user)

    return resume_subscription(
        db=db,
        subscription_id=subscription_id,
        customer_id=customer.id
    )


# ----------------------------------------------------------------------
# 7. Cancel Subscription [CUSTOMER, ORG_ADMIN]
# ----------------------------------------------------------------------

@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionOut
)
def cancel_subscription_api(
    subscription_id: int,
    data: CancelRequest,
    db: db_dependency,
    current_user=Depends(
        require_roles(Role.CUSTOMER, Role.ORG_ADMIN)
    )
):

    if current_user.role == Role.CUSTOMER:

        customer = get_current_customer(db, current_user)

        return cancel_subscription(
            db=db,
            subscription_id=subscription_id,
            customer_id=customer.id,
            at_period_end=data.at_period_end
        )

    return cancel_subscription_by_admin(
        db=db,
        subscription_id=subscription_id,
        organization_id=current_user.organization_id,
        at_period_end=data.at_period_end
    )
