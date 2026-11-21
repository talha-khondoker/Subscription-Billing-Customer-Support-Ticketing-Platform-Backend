# ----------------------------------------------------------------------
# app/services/plan_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_plan
#   - update_plan
#   - list_plans(db, user)
#   - set_plan_active(db, id, flag)

# ----------------------------------------------------------------------
# app/services/plan_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models.
# ----------------------------------------------------------------------

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate


# ---------------------------------
# 1. Create Plan
# ---------------------------------
def create_plan(
    db: Session,
    plan_data: PlanCreate,
    organization_id: int
):
    existing_plan = db.query(Plan).filter(
        Plan.organization_id == organization_id,
        Plan.name == plan_data.name
    ).first()

    if existing_plan:
        raise HTTPException(
            status_code=409,
            detail="Plan name already exists"
        )

    new_plan = Plan(
        organization_id=organization_id,
        **plan_data.model_dump()
    )

    try:
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Plan already exists or invalid organization"
        )

    return new_plan


# ---------------------------------
# 2. Update Plan
# ---------------------------------
def update_plan(
    db: Session,
    plan_id: int,
    organization_id: int,
    plan_data: PlanUpdate
):
    existing_plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.organization_id == organization_id
    ).first()

    if existing_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    update_data = plan_data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:

        duplicate = db.query(Plan).filter(
            Plan.organization_id == organization_id,
            Plan.name == update_data["name"],
            Plan.id != plan_id
        ).first()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Plan name already exists"
            )

    for key, value in update_data.items():
        setattr(existing_plan, key, value)

    try:
        db.commit()
        db.refresh(existing_plan)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update plan"
        )

    return existing_plan


# ---------------------------------
# 3. List Plans
# ---------------------------------
def list_plans(
    db: Session,
    organization_id: int,
    is_customer: bool = False
):
    query = db.query(Plan).filter(
        Plan.organization_id == organization_id
    )

    if is_customer:
        query = query.filter(
            Plan.is_active.is_(True)
        )

    return query.all()


# ---------------------------------
# 4. Set Plan Active / Inactive
# ---------------------------------
def set_plan_active(
    db: Session,
    plan_id: int,
    organization_id: int,
    flag: bool
):
    existing_plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.organization_id == organization_id
    ).first()

    if existing_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    existing_plan.is_active = flag

    try:
        db.commit()
        db.refresh(existing_plan)
        return existing_plan

    except Exception:
        db.rollback()
        raise
