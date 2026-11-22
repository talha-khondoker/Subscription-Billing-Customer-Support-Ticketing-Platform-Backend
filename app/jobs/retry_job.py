# ----------------------------------------------------------------------
# app/jobs/retry_job.py
# Owner:   Member 4
# Purpose: Retry failed payments that are due.
# ----------------------------------------------------------------------
# TODO:
#   - call retry_service.run_due_retries
#   - also callable from POST /admin/jobs/run-retries

"""Run due retries in a short lived database session."""
import logging

from app.core.database import SessionLocal
from app.services.retry_service import run_due_retries

logger = logging.getLogger("subflow.jobs.retry")


def run_retries(organization_id: int | None = None) -> dict[str, int]:
    db = SessionLocal()
    try:
        result = run_due_retries(db, organization_id=organization_id)
        return {"retried": len(result)}
    except Exception:
        db.rollback()
        logger.exception("Payment retry cycle failed")
        raise
    finally:
        db.close()
