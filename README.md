Stack: FastAPI, SQLAlchemy 2, MySQL (SQLite for local work), JWT auth, APScheduler.

## How to use
1. Put this folder in the shared Git repo and push to `main`.
2. Each member opens only their own files (see Owner in each header) and fills in the TODO list.
3. Shared files (core/, utils/, main.py) belong to Member 1. Ask before changing them.
4. The finished SQLAlchemy models are in the separate `subflow-backend-models.zip`; copy them over the model placeholders on Day 1.

## Layers
router (HTTP only) -> service (business rules) -> model (tables). Jobs only call services.

## Owners
- Member 1: auth, organizations, users, audit, core files, deployment
- Member 2: plans, subscriptions
- Member 3: invoices, proration, invoice numbers
- Member 4: payments, mock gateway, retries, refunds, renewal and retry jobs, scheduler
- Member 5: tickets, assignment, SLA, billing context, SLA job
- Member 6: customers, dashboards, notifications, seed data
