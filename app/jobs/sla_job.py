# ----------------------------------------------------------------------
# app/jobs/sla_job.py
# Owner:   Member 5
# Purpose: Check SLA deadlines.
# ----------------------------------------------------------------------


"""SLA breach job. Owner: Member 5.

Member 4's scheduler.py registers it:
    from app.jobs.sla_job import run_sla_check
    scheduler.add_job(run_sla_check, "interval", minutes=5, id="sla_check", replace_existing=True)

Member 4's POST /admin/jobs/run-sla-check calls run_sla_check() and returns its dict.
"""
import logging

from app.core.database import SessionLocal
from app.services import sla_service

logger = logging.getLogger("subflow.jobs.sla")


def run_sla_check() -> dict:
    """Open its own DB session, check all tickets, return a summary dict."""
    db = SessionLocal()
    try:
        summary = sla_service.check_breaches(db)
        if summary["first_response_breaches"] or summary["resolution_breaches"]:
            logger.info("SLA check: %s", summary)
        return summary
    except Exception:
        db.rollback()
        logger.exception("SLA check failed")
        raise
    finally:
        db.close()
