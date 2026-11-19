# ----------------------------------------------------------------------
"""APScheduler lifecycle. Job modules may expose run_* functions as they are implemented."""
import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # The API can still run when optional runtime dependencies are not installed.
    BackgroundScheduler = None

from app.core.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC") if BackgroundScheduler else None


def _run_if_available(module_name, function_name):
    from importlib import import_module
    module = import_module(module_name)
    callback = getattr(module, function_name, None)
    if callback is None:
        logger.warning("Scheduled job %s.%s is not implemented yet", module_name, function_name)
        return
    callback()


def start_scheduler():
    if not settings.SCHEDULER_ENABLED or scheduler is None or scheduler.running:
        return
    scheduler.add_job(_run_if_available, "interval", id="renewals", days=1,
                      args=["app.jobs.renewal_job", "run_renewals"], replace_existing=True)
    scheduler.add_job(_run_if_available, "interval", id="retries", hours=1,
                      args=["app.jobs.retry_job", "run_retries"], replace_existing=True)
    scheduler.add_job(_run_if_available, "interval", id="sla", minutes=5,
                      args=["app.jobs.sla_job", "run_sla_check"], replace_existing=True)
    scheduler.start()


def stop_scheduler():
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
# app/jobs/scheduler.py
# Owner:   Member 4
# Purpose: APScheduler setup.
# ----------------------------------------------------------------------
# TODO:
#   - create scheduler
#   - register renewal_job (daily), retry_job (hourly), sla_job (every 5 minutes)
#   - start_scheduler() / stop_scheduler()
#   - do nothing when SCHEDULER_ENABLED is false

# This file should contain only APScheduler setup and job registration.
