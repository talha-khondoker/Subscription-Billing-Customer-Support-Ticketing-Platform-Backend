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


from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers import admin_jobs, audit, auth, customers, dashboard, invoices, notifications
from app.routers import organizations, payments, plans, sla, subscriptions, tickets, users

ROUTERS = (admin_jobs, audit, auth, customers, dashboard, invoices, notifications,
           organizations, payments, plans, sla, subscriptions, tickets, users)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SCHEDULER_ENABLED:
        start_scheduler()
    yield
    if settings.SCHEDULER_ENABLED:
        stop_scheduler()


app = FastAPI(title="SubFlow API", version="1.0.0",
              description="Subscription billing and customer support API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)
for module in ROUTERS:
    router = getattr(module, "router", None)
    if router is not None:
        app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
