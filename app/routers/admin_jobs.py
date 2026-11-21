# ----------------------------------------------------------------------
# app/routers/admin_jobs.py
# Owner:   Member 4
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST /admin/jobs/run-renewals [OA]  manual trigger (demo)
#   - POST /admin/jobs/run-retries [OA]  manual trigger (demo)
#   - POST /admin/jobs/run-sla-check [OA]  manual trigger (demo)

from fastapi import APIRouter, Depends

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
    return sla_job.run_sla_check()
