# ----------------------------------------------------------------------
# app/routers/admin_jobs.py
# Owner:   Member 4
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import current_org_admin
from app.jobs import renewal_job, retry_job, sla_job
from app.models.user import User

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


@router.post("/run-renewals")
def run_renewals(user: User = Depends(current_org_admin)):
    return renewal_job.run_renewals(organization_id=user.organization_id)


@router.post("/run-retries")
def run_retries(user: User = Depends(current_org_admin)):
    return retry_job.run_retries(organization_id=user.organization_id)


@router.post("/run-sla-check")
def run_sla_check(_user: User = Depends(current_org_admin)):
    check = getattr(sla_job, "run_sla_check", None)
    if check is None:
        raise HTTPException(status_code=503, detail="SLA check job is not available")
    return check()
