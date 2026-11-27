# ----------------------------------------------------------------------
# app/services/plan_service.py
# Owner:   Member 2
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate
from sqlalchemy.exc import IntegrityError

from app.services import audit_service

def _snapshot(plan):
    """JSON-safe copy of the plan fields (for the audit log)."""
    return {"name": plan.name, "price": str(plan.price), "billing_period": getattr(plan.billing_period, "value", str(plan.billing_period)),
            "tax_percent": str(plan.tax_percent), "is_active": plan.is_active}


# ---------------------------------
# 1. Create Plan
# ---------------------------------

# 1. Create Plan
def create_plan(db: Session,plan_data: PlanCreate,organization_id: int, actor=None):

    existing_plan = db.query(Plan).filter( Plan.organization_id == organization_id, Plan.name == plan_data.name ).first()

    if existing_plan:
        raise HTTPException( status_code=409,detail="Plan name already exists" )

    new_plan = Plan(organization_id=organization_id,**plan_data.model_dump())

    try:
        db.add(new_plan)
        db.flush()
        audit_service.log(db, actor, "plan.create", "plan", new_plan.id, None, _snapshot(new_plan))
        db.commit()
        db.refresh(new_plan)

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Plan already exists or invalid organization")

    return new_plan


# 2. Update Plan
def update_plan( db: Session, plan_id: int, organization_id: int, plan_data: PlanUpdate, actor=None
):

    existing_plan = db.query(Plan).filter( Plan.id == plan_id, Plan.organization_id == organization_id).first()

    if existing_plan is None:
        raise HTTPException(status_code=404,  detail="Plan not found")

    update_data = plan_data.model_dump( exclude_unset=True )

    if "name" in update_data and update_data["name"] is not None:

        duplicate = db.query(Plan).filter( Plan.organization_id == organization_id, Plan.name == update_data["name"], Plan.id != plan_id).first()

        if duplicate:
            raise HTTPException( status_code=409,detail="Plan name already exists" )

    old_values = _snapshot(existing_plan)
    for key, value in update_data.items():
        setattr(existing_plan, key, value)

    try:
        db.flush()
        audit_service.log(db, actor, "plan.update", "plan", existing_plan.id, old_values, _snapshot(existing_plan))
        db.commit()
        db.refresh(existing_plan)

    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=409, detail="Could not update plan")
    return existing_plan


# 3. List Plans
def list_plans( db: Session, organization_id: int, is_customer: bool = False):

    query = db.query(Plan).filter(
        Plan.organization_id == organization_id)

    if is_customer:
        query = query.filter(Plan.is_active.is_(True))

    return query.all()


# 4. Set Plan Active / Inactive
def set_plan_active( db: Session, plan_id: int,organization_id: int,  flag: bool
):

    existing_plan = db.query(Plan).filter( Plan.id == plan_id, Plan.organization_id == organization_id ).first()

    if existing_plan is None:
        raise HTTPException( status_code=404, detail="Plan not found" )

    existing_plan.is_active = flag

    db.commit()
    db.refresh(existing_plan)

    return existing_plan
