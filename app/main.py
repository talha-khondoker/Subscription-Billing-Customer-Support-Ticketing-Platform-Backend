# ----------------------------------------------------------------------
# app/main.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: FastAPI application entry point.
# ----------------------------------------------------------------------
# TODO:
#   - create the FastAPI app (title, version, description)
#   - add CORS middleware using settings.CORS_ORIGINS
#   - register exception handlers from core/exceptions.py
#   - include every router under the /api/v1 prefix
#   - on startup: start the scheduler when settings.SCHEDULER_ENABLED is true
#   - on shutdown: stop the scheduler
#   - add a GET /health endpoint


"""SubFlow API entry point.

Run locally from the project root:
    uvicorn app.main:app --reload
Interactive API docs:
    http://localhost:8000/docs

Conventions
-----------
* Every router file exposes a module-level ``router = APIRouter(tags=[...])`` and writes
  the FULL path after the prefix (for example ``@router.get("/plans")`` or
  ``@router.post("/invoices/{invoice_id}/pay")``). This file adds the ``/api/v1`` prefix.
* To add a new router: create ``app/routers/<name>.py`` and add ``"<name>"`` to ROUTER_MODULES.
* A router file that does not define ``router`` yet (an empty placeholder) is skipped with a
  warning, so the app keeps starting while the team is still writing code.
"""
import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models as _models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import settings
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("subflow")

API_PREFIX = "/api/v1"

# Router modules inside app/routers/. Order controls the order of groups in Swagger.
ROUTER_MODULES = [
    "auth",
    "organizations",
    "users",
    "plans",
    "subscriptions",
    "invoices",
    "payments",
    "customers",
    "tickets",
    "sla",
    "dashboard",
    "notifications",
    "audit",
    "admin_jobs",
]

OPENAPI_TAGS = [
    {"name": "auth", "description": "Register, login and current user"},
    {"name": "organizations", "description": "Super Admin: manage organizations"},
    {"name": "users", "description": "Org Admin: manage support agents"},
    # {"name": "plans", "description": "Subscription plans"},
    # {"name": "subscriptions", "description": "Subscribe, upgrade/downgrade, pause/resume, cancel"},
    # {"name": "invoices", "description": "Invoices and invoice items"},
    {"name": "payments", "description": "Payments, retries, refunds, mock gateway"},
    {"name": "customers", "description": "Customer profiles and history"},
    {"name": "tickets", "description": "Support tickets and Billing-to-Ticket View"},
    {"name": "sla", "description": "SLA policies"},
    {"name": "dashboard", "description": "Role dashboards"},
    {"name": "notifications", "description": "In-app notifications"},
    {"name": "audit", "description": "Audit log"},
    {"name": "admin-jobs", "description": "Manual triggers for background jobs (demo)"},
]


# --------------------------------------------------------------------------- helpers
def _scheduler_hooks():
    """Return (start, stop) functions of the scheduler, or (None, None) if not written yet."""
    try:
        from app.jobs import scheduler

        return scheduler.start_scheduler, scheduler.stop_scheduler
    except (ImportError, AttributeError):
        logger.warning("Scheduler is not implemented yet (app/jobs/scheduler.py); background jobs are off.")
        return None, None


def register_routers(application: FastAPI) -> None:
    """Import each router module and include it under /api/v1."""
    for name in ROUTER_MODULES:
        module = importlib.import_module(f"app.routers.{name}")
        router = getattr(module, "router", None)
        if router is None:
            logger.warning("Router '%s' has no `router` yet; skipped.", name)
            continue
        application.include_router(router, prefix=API_PREFIX)
        logger.info("Router registered: %s", name)


def register_error_handlers(application: FastAPI) -> None:
    """Attach the shared error handlers (consistent {"detail", "code"} responses)."""
    try:
        from app.core.exceptions import register_exception_handlers
    except ImportError:
        logger.warning("core/exceptions.py is not implemented yet; using FastAPI default errors.")
        return
    register_exception_handlers(application)


# --------------------------------------------------------------------------- lifespan
@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup
    if settings.ENV == "development":
        # Convenience for local work. Switch to Alembic migrations before production.
        Base.metadata.create_all(bind=engine)
        logger.info("Development mode: tables ensured.")

    start_scheduler, stop_scheduler = _scheduler_hooks()
    scheduler_running = False
    if settings.SCHEDULER_ENABLED and start_scheduler:
        start_scheduler()
        scheduler_running = True
        logger.info("Scheduler started.")

    yield

    # Shutdown
    if scheduler_running and stop_scheduler:
        stop_scheduler()
        logger.info("Scheduler stopped.")


# --------------------------------------------------------------------------- app
app = FastAPI(
    title="SubFlow API",
    version="1.0.0",
    description=(
        "Subscription Billing & Customer Support Ticketing Platform. "
        "Roles: Super Admin, Org Admin, Support Agent, Customer."
    ),
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
register_routers(app)


# --------------------------------------------------------------------------- basic endpoints
@app.get("/", include_in_schema=False)
def root():
    return {"name": "SubFlow API", "docs": "/docs", "api_prefix": API_PREFIX}


@app.get("/health", tags=["health"])
def health():
    """Liveness check, used by Render and by the frontend team."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    """Readiness check: confirms the database connection works."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database health check failed")
        return {"status": "error", "database": "unreachable", "detail": str(exc)}
    return {"status": "ok", "database": "reachable"}
