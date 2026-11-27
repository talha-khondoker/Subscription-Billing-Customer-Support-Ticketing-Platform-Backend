# ----------------------------------------------------------------------
# app/jobs/scheduler.py
# Owner:   Member 4
# Purpose: APScheduler setup.
# ----------------------------------------------------------------------

# This file should contain only APScheduler setup and job registration.

import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

from app.core.config import settings

logger = logging.getLogger("subflow.jobs.scheduler")
scheduler = (
    BackgroundScheduler(
        timezone="UTC",
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
    )
    if BackgroundScheduler is not None
    else None
)


def _run_if_available(module_name: str, function_name: str) -> None:
    from importlib import import_module

    module = import_module(module_name)
    callback = getattr(module, function_name, None)
    if callback is None:
        logger.warning("Scheduled job %s.%s is not implemented", module_name, function_name)
        return
    callback()


def start_scheduler() -> None:
    if not settings.SCHEDULER_ENABLED or scheduler is None or scheduler.running:
        return
    scheduler.add_job(
        _run_if_available, "interval", id="renewals", days=1,
        args=["app.jobs.renewal_job", "run_renewals"], replace_existing=True,
    )
    scheduler.add_job(
        _run_if_available, "interval", id="retries", hours=1,
        args=["app.jobs.retry_job", "run_retries"], replace_existing=True,
    )
    scheduler.add_job(
        _run_if_available, "interval", id="sla", minutes=5,
        args=["app.jobs.sla_job", "run_sla_check"], replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
