# ----------------------------------------------------------------------
# app/routers/dashboard.py
# Owner:   Member 6
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1


"""Dashboard endpoints. Owner: Member 6. Paths are full; main.py adds /api/v1."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_agent, current_customer, current_org_admin, current_super_admin
from app.models.user import User
from app.schemas.dashboard import AdminDashboard, AgentDashboard, CustomerDashboard, PlatformDashboard
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/platform", response_model=PlatformDashboard)
def platform_dashboard(db: Session = Depends(get_db), user: User = Depends(current_super_admin)):
    return dashboard_service.platform_dashboard(db, user)


@router.get("/dashboard/admin", response_model=AdminDashboard)
def admin_dashboard(
    days: int = Query(30, ge=1, le=365, description="length of the reporting period in days"),
    db: Session = Depends(get_db),
    user: User = Depends(current_org_admin),
):
    return dashboard_service.admin_dashboard(db, user, days)


@router.get("/dashboard/agent", response_model=AgentDashboard)
def agent_dashboard(
    days: int = Query(7, ge=1, le=365, description="length of the reporting period in days"),
    db: Session = Depends(get_db),
    user: User = Depends(current_agent),
):
    return dashboard_service.agent_dashboard(db, user, days)


@router.get("/dashboard/customer", response_model=CustomerDashboard)
def customer_dashboard(db: Session = Depends(get_db), user: User = Depends(current_customer)):
    return dashboard_service.customer_dashboard(db, user)
