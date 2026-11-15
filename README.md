## Subscription Billing & Customer Support Ticketing Platform


A multi-tenant subscription management and customer support backend
built with **FastAPI, SQLAlchemy, and MySQL**. SubFlow provides
subscription and billing workflows, payment retry handling, customer
support tickets, SLA monitoring, role-based access control,
notifications, audit logging, and operational dashboards.

> **Project scope:** Tier 1 backend structure. Authentication uses JWT
> with role-based access. Payments are handled through a mock gateway
> for demonstration.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Core Features](#core-features)
-   [Technology Stack](#technology-stack)
-   [Architecture](#architecture)
-   [User Roles](#user-roles)
-   [Project Structure](#project-structure)
-   [Getting Started](#getting-started)
-   [Environment Configuration](#environment-configuration)
-   [Database and Seed Data](#database-and-seed-data)
-   [Running the Application](#running-the-application)
-   [API Documentation](#api-documentation)
-   [API Overview](#api-overview)
-   [Background Jobs](#background-jobs)
-   [Business Rules](#business-rules)
-   [Testing](#testing)
-   [Team Responsibilities](#team-responsibilities)
-   [Development Conventions](#development-conventions)

------------------------------------------------------------------------

## Overview

Subscription Billing & Customer Support Ticketing Platform is designed to help organizations manage customer subscriptions
and billing while providing an integrated support-ticket workflow.

The backend follows a layered architecture so that features can be
developed independently while sharing consistent security, database, and
service conventions.

### Main capabilities

-   Organization and user management
-   JWT authentication and role-based authorization
-   Organization-scoped data access
-   Subscription plans and lifecycle management
-   Subscription upgrades, downgrades, and proration
-   Invoice generation and payment processing through a mock gateway
-   Automatic payment retry scheduling and refunds
-   Customer profiles and billing history
-   Support tickets, agent assignment, and internal notes
-   SLA deadlines, breach detection, and escalation
-   In-app notifications and audit logs
-   Role-specific dashboards
-   Scheduled jobs with manual demo triggers

------------------------------------------------------------------------

## Core Features

  -----------------------------------------------------------------------
  Area                                Description
  ----------------------------------- -----------------------------------
  Authentication                      Customer registration, login, JWT
                                      creation, and current-user profile

  Organizations                       Super Admin can create, list,
                                      enable, disable, and update
                                      organizations

  User management                     Organization Admin can manage
                                      support agents

  Plans                               Create, update, activate, and
                                      deactivate subscription plans

  Subscriptions                       Subscribe, pause, resume, cancel,
                                      upgrade, and downgrade

  Billing                             Generate invoices, calculate tax,
                                      and create proration invoice items

  Payments                            Mock payment processing, payment
                                      attempts, retries, and refunds

  Customers                           Customer profiles and subscription,
                                      invoice, payment, and ticket
                                      history

  Support tickets                     Ticket creation, replies, internal
                                      notes, assignment, escalation, and
                                      resolution

  SLA                                 Priority-based response and
                                      resolution deadlines with breach
                                      monitoring

  Dashboards                          Platform, organization admin,
                                      agent, and customer dashboards

  Notifications                       In-app notifications and
                                      read/unread management

  Audit                               Record important actions and
                                      before/after values
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Technology Stack

  Technology    Purpose
  ------------- ---------------------------------
  Python        Backend programming language
  FastAPI       REST API framework
  SQLAlchemy    ORM and database access
  MySQL         Relational database
  Pydantic      Request and response validation
  JWT           Token-based authentication
  APScheduler   Scheduled background jobs
  Alembic       Database migrations
  Pytest        Automated testing

The exact package versions are defined in `requirements.txt`.

------------------------------------------------------------------------

## Architecture

The application uses a layered architecture. Keep each layer focused on
its responsibility.

  -----------------------------------------------------------------------
  Layer                   Location                Responsibility
  ----------------------- ----------------------- -----------------------
  Router                  `app/routers/`          Handles HTTP requests,
                                                  authorization, service
                                                  calls, and responses

  Service                 `app/services/`         Contains business rules
                                                  and coordinates
                                                  database operations

  Model                   `app/models/`           Defines SQLAlchemy
                                                  tables, columns, and
                                                  relationships

  Schema                  `app/schemas/`          Defines Pydantic
                                                  request and response
                                                  contracts

  Jobs                    `app/jobs/`             Runs scheduled tasks by
                                                  calling services
  -----------------------------------------------------------------------

### Example request flow

When a customer subscribes to a plan:

1.  `POST /subscriptions` receives the request.
2.  `subscription_service` creates the subscription.
3.  `invoice_service` generates the initial invoice.
4.  `payment_service` attempts payment through `mock_gateway`.
5.  If payment fails, `retry_service` schedules the next attempt.
6.  `notification_service` sends the relevant in-app notification.
7.  `audit_service` records the important action.

**Important:** Routers should not contain business rules. Background
jobs should call services rather than duplicating business logic.

------------------------------------------------------------------------

## User Roles

SubFlow defines four roles:

  -----------------------------------------------------------------------
  Role                                Key permissions
  ----------------------------------- -----------------------------------
  `super_admin`                       Manage organizations and view
                                      platform-level dashboard data

  `org_admin`                         Manage organization users, plans,
                                      customers, billing operations,
                                      tickets, SLA policies, and audit
                                      logs

  `agent`                             Work on assigned support tickets
                                      and access permitted customer and
                                      billing context

  `customer`                          Manage their own profile,
                                      subscriptions, invoices, payments,
                                      and support tickets
  -----------------------------------------------------------------------

All endpoints require a JWT except customer registration and login.
Authorization must be enforced on protected routes.

### Organization data isolation

Organization-owned data must always be scoped to the authenticated
user's `organization_id`. Use the shared helper in `app/core/tenancy.py`
for organization-scoped queries.

Customers may only access their own records. Internal ticket notes must
never be returned to customers.

------------------------------------------------------------------------

## Project Structure

``` text
subflow-backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── deps.py
│   │   ├── tenancy.py
│   │   ├── enums.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── organization.py
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── invoice.py
│   │   ├── payment.py
│   │   ├── ticket.py
│   │   ├── sla_policy.py
│   │   ├── notification.py
│   │   └── audit_log.py
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   ├── jobs/
│   │   ├── scheduler.py
│   │   ├── renewal_job.py
│   │   ├── retry_job.py
│   │   └── sla_job.py
│   └── utils/
├── alembic/
├── scripts/
│   ├── seed.py
│   └── reset_db.py
├── tests/
├── .env.example
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

The `schemas/`, `routers/`, and `services/` directories contain
feature-specific modules such as authentication, organizations, plans,
subscriptions, invoices, payments, tickets, dashboards, notifications,
and audit.

------------------------------------------------------------------------

## Getting Started

### Prerequisites

Make sure you have the following installed:

-   Python
-   MySQL Server
-   Git
-   pip

### 1. Clone the repository

``` bash
git clone <YOUR_REPOSITORY_URL>
cd subflow-backend
```

Replace `<YOUR_REPOSITORY_URL>` with the Git repository URL.

### 2. Create and activate a virtual environment

**Windows PowerShell**

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows Command Prompt**

``` cmd
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file:

**Windows**

``` powershell
Copy-Item .env.example .env
```

**macOS / Linux**

``` bash
cp .env.example .env
```

Update `.env` with your local MySQL connection details and the required
application settings.

### 5. Prepare the database

Create the MySQL database configured in `DATABASE_URL`, then run the
project's database setup and seed script:

``` bash
python scripts/reset_db.py
```

> **Warning:** `reset_db.py` is intended for development/demo setup. A
> reset script may drop existing tables and data. Do not run it against
> a database containing data you need to keep.

### 6. Start the development server

``` bash
uvicorn app.main:app --reload
```

The API will be available at:

``` text
http://localhost:8000
```

------------------------------------------------------------------------

## Environment Configuration

The application configuration is read from `.env` through
`app/core/config.py`.

The backend structure defines the following settings:

  -----------------------------------------------------------------------
  Variable                            Purpose
  ----------------------------------- -----------------------------------
  `DATABASE_URL`                      SQLAlchemy database connection URL

  `SECRET_KEY`                        Secret used for JWT signing

  `ACCESS_TOKEN_EXPIRE_MINUTES`       JWT access-token lifetime

  `RETRY_SCHEDULE_DAYS`               Day offsets used for payment retry
                                      scheduling; default schedule is 1,
                                      3, and 5

  `MAX_RETRY_ATTEMPTS`                Maximum payment retry attempts;
                                      default is 3

  `SCHEDULER_ENABLED`                 Enables or disables scheduled
                                      background jobs

  `CORS_ORIGINS`                      Allowed frontend origins

  `DEFAULT_TAX_PERCENT`               Default tax percentage
  -----------------------------------------------------------------------

Use `.env.example` as the source of truth for the exact variable format
expected by the application.

**Security notes**

-   Never commit `.env` or real credentials.
-   Use a strong, unique `SECRET_KEY`.
-   Keep production database credentials out of source control.
-   Configure `CORS_ORIGINS` for the frontend environments that should
    be allowed.

------------------------------------------------------------------------

## Database and Seed Data

The backend uses SQLAlchemy models with MySQL. Tables include common
`id`, `created_at`, and `updated_at` fields. Organization-scoped tables
also include `organization_id`.

Money values use `Decimal(12,2)`.

### Main database tables

  -----------------------------------------------------------------------
  Table                               Purpose
  ----------------------------------- -----------------------------------
  `organizations`                     Organization records and status

  `users`                             Login identities, roles, and
                                      organization membership

  `customers`                         Customer profile information

  `plans`                             Subscription plan details and
                                      pricing

  `subscriptions`                     Customer subscription lifecycle and
                                      billing periods

  `invoices`                          Invoice totals, status, and billing
                                      periods

  `invoice_items`                     Plan, proration, and discount line
                                      items

  `payments`                          Payment records and gateway results

  `payment_attempts`                  Payment attempt history and retry
                                      timing

  `refunds`                           Full and partial refund records

  `sla_policies`                      First-response and resolution
                                      targets

  `tickets`                           Support requests, assignment,
                                      status, and SLA tracking

  `ticket_messages`                   Customer replies, agent replies,
                                      and internal notes

  `notifications`                     In-app user notifications

  `audit_logs`                        Actor, action, entity, and
                                      before/after values
  -----------------------------------------------------------------------

### Seed data

The demo seed setup is intended to create:

-   1 Super Admin
-   2 organizations, each with 1 Organization Admin
-   2 support agents
-   5 customers
-   3 subscription plans
-   Sample invoices, payments, and support tickets

Use the seed script to populate development/demo data. Refer to the
project implementation for the actual demo credentials.

------------------------------------------------------------------------

## Running the Application

Start the API server:

``` bash
uvicorn app.main:app --reload
```

For a different port or host:

``` bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Disable scheduled jobs for local testing by setting:

``` env
SCHEDULER_ENABLED=false
```

------------------------------------------------------------------------

## API Documentation

FastAPI provides interactive API documentation when the server is
running:

-   **Swagger UI:** `http://localhost:8000/docs`
-   **ReDoc:** `http://localhost:8000/redoc`

The API base path is:

``` text
/api/v1
```

Register and login are public. All other routes require a valid JWT,
subject to their role permissions.

------------------------------------------------------------------------

## API Overview

The following is a feature-level overview of the Tier 1 API. See Swagger
UI for request schemas, response schemas, and the complete registered
route list.

  ----------------------------------------------------------------------------------------
  Area                    Example endpoints                        Access
  ----------------------- ---------------------------------------- -----------------------
  Auth                    `POST /auth/register`,                   Public / authenticated
                          `POST /auth/login`, `GET /auth/me`       

  Organizations           `POST /organizations`,                   Super Admin
                          `GET /organizations`,                    
                          `PATCH /organizations/{id}`              

  Agents                  `POST /users/agents`,                    Org Admin
                          `GET /users/agents`, `PATCH /users/{id}` 

  Plans                   `POST /plans`, `GET /plans`,             Org Admin / Agent /
                          `PATCH /plans/{id}`                      Customer as permitted

  Subscriptions           `POST /subscriptions`,                   Customer / Org Admin /
                          `GET /subscriptions/me`,                 Agent as permitted
                          `POST /subscriptions/{id}/change-plan`   

  Invoices                `GET /invoices/me`, `GET /invoices`,     Customer / Org Admin /
                          `GET /invoices/{id}`                     Agent as permitted

  Payments                `POST /invoices/{id}/pay`,               Customer / Org Admin /
                          `GET /payments/me`, `GET /payments`,     Agent as permitted
                          `POST /payments/{id}/refund`             

  Customers               `GET /customers/me`,                     Customer / Org Admin /
                          `PATCH /customers/me`, `GET /customers`, Agent as permitted
                          `GET /customers/{id}`                    

  Tickets                 `POST /tickets`, `GET /tickets`,         Customer / Agent / Org
                          `GET /tickets/{id}`,                     Admin
                          `POST /tickets/{id}/messages`            

  SLA                     `/sla-policies`                          Org Admin

  Dashboards              `/dashboard/platform`,                   Role-specific
                          `/dashboard/admin`, `/dashboard/agent`,  
                          `/dashboard/customer`                    

  Notifications           `GET /notifications`,                    Authenticated users
                          `POST /notifications/{id}/read`,         
                          `POST /notifications/read-all`           

  Audit                   `GET /audit-logs`                        Org Admin

  Demo jobs               `POST /admin/jobs/run-renewals`,         Org Admin
                          `/run-retries`, `/run-sla-check`         
  ----------------------------------------------------------------------------------------

------------------------------------------------------------------------

## Background Jobs

APScheduler is used to run recurring backend tasks.

  -----------------------------------------------------------------------
  Job                     Schedule                Responsibility
  ----------------------- ----------------------- -----------------------
  `renewal_job`           Daily                   Finds subscriptions due
                                                  for renewal, creates
                                                  invoices, and attempts
                                                  payment

  `retry_job`             Hourly                  Retries failed payments
                                                  when `next_retry_at` is
                                                  due

  `sla_job`               Every 5 minutes         Flags SLA breaches,
                                                  escalates overdue
                                                  tickets, and sends
                                                  notifications
  -----------------------------------------------------------------------

For demonstrations and manual testing, the jobs can also be triggered
through:

-   `POST /api/v1/admin/jobs/run-renewals`
-   `POST /api/v1/admin/jobs/run-retries`
-   `POST /api/v1/admin/jobs/run-sla-check`

Scheduled jobs can be disabled with `SCHEDULER_ENABLED=false`.

------------------------------------------------------------------------

## Business Rules

Key business logic belongs in services, not routers.

### Subscription proration

When a customer changes plans during a billing period:

``` text
credit = old_price × remaining_days / period_days
charge = new_price × remaining_days / period_days
net proration = charge - credit
```

The net amount is recorded as a proration invoice item.

### Invoice calculation

``` text
subtotal = sum(invoice items)
tax = (subtotal - discount) × tax_percent
total = subtotal - discount + tax
```

Invoice numbers follow this format:

``` text
INV-<org>-<yyyymm>-<seq>
```

### Payment retries

-   The default retry schedule is 1, 3, and 5 days.
-   The default maximum is 3 attempts.
-   After the final failed retry, the subscription becomes `past_due`
    and the admin is notified.

### Refunds

A refund cannot exceed the original paid amount minus previous refunds.
A full refund changes the payment and invoice status to `refunded`.
Refunds must be audit-logged.

### Ticket assignment and SLA

-   New tickets are assigned to the active agent with the fewest open
    tickets.
-   SLA deadlines are calculated from the ticket priority's policy.
-   The first agent reply records `first_responded_at`.
-   The SLA job checks deadlines and sets breach flags.

### Default SLA targets

  Priority     First response   Resolution
  ---------- ---------------- ------------
  Urgent           15 minutes      4 hours
  High                 1 hour      8 hours
  Medium              4 hours     24 hours
  Low                 8 hours     72 hours

Organization Admins can edit SLA policies.

------------------------------------------------------------------------

## Testing

Run the test suite from the project root:

``` bash
pytest
```

The minimum required test areas are:

-   Authentication and role permissions
-   Organization tenancy isolation
-   Subscription proration
-   Payment retry schedule
-   SLA deadlines and breach handling
-   Billing context response

Keep scheduled jobs disabled during tests when appropriate:

``` env
SCHEDULER_ENABLED=false
```

------------------------------------------------------------------------

## Team Responsibilities

The project is structured for a six-member team. The ownership split
below helps reduce conflicts and makes parallel development easier.

  -----------------------------------------------------------------------
  Member                  Module ownership        Main responsibilities
  ----------------------- ----------------------- -----------------------
  Member 1                Auth, organizations,    Authentication,
                          users, audit            organization/user
                                                  management, audit
                                                  logging

  Member 2                Plans and subscriptions Plan management and
                                                  subscription lifecycle

  Member 3                Invoices and billing    Invoice generation and
                                                  proration

  Member 4                Payments and retries    Payments, mock gateway,
                                                  retries, refunds,
                                                  renewal/retry jobs

  Member 5                Tickets and SLA         Ticket workflow,
                                                  assignment, SLA
                                                  policies, billing
                                                  context, SLA job

  Member 6                Customers and           Customer management,
                          dashboards              dashboards,
                                                  notifications
  -----------------------------------------------------------------------

### Shared-file ownership

The following shared areas are owned by Member 1:

-   `app/core/`
-   `app/utils/`
-   `app/main.py`

**Coordinate with Member 1 before changing shared files.** Agree on
shared model, schema, enum, and service interfaces before integrating
dependent modules.

------------------------------------------------------------------------

## Development Conventions

Please follow these conventions throughout the codebase:

1.  **Naming:** Use `snake_case` for files, functions, and JSON fields.
    Use plural nouns for route collections and one router file per
    feature area.

2.  **Layering:** Keep HTTP handling in routers and business rules in
    services. Jobs should call services.

3.  **Responses:** List endpoints should return a consistent paginated
    structure:

    ``` json
    {
      "items": [],
      "total": 0,
      "page": 1,
      "page_size": 10
    }
    ```

4.  **Errors:** Return the shared error structure:

    ``` json
    {
      "detail": "A readable error message",
      "code": "ERROR_CODE"
    }
    ```

5.  **Security:** Scope organization data through `tenancy.scoped()`.
    Enforce ownership checks for customer resources and hide internal
    ticket notes from customers.

6.  **Money and time:** Use `Decimal` for money. Store datetimes in UTC
    and serialize them as ISO 8601.

7.  **Transactions:** Use one database transaction per request. Services
    should commit once at the end of a use case.

8.  **Audit logging:** Plan changes, invoice changes, refunds, ticket
    reassignments, and subscription cancellations must be recorded
    through `audit_service.log`.

9.  **Consistency:** Keep role and status values in the shared enums
    module so API behavior remains consistent.

------------------------------------------------------------------------

## Contributing

1.  Pull the latest changes before starting work.
2.  Work only within your assigned module unless a shared change has
    been agreed upon.
3.  Coordinate changes to shared models, schemas, enums, dependencies,
    and core utilities.
4.  Test your feature before opening a pull request.
5.  Include a clear description of the change and any relevant test
    results in your pull request.
6.  Do not commit `.env`, credentials, database dumps, or local
    virtual-environment files.

------------------------------------------------------------------------

## Project Status

This README documents the **SubFlow Backend Tier 1 structure and
intended behavior**. Confirm implementation details, exact package
versions, environment variable formatting, and demo login credentials
against the current source code before using them.

------------------------------------------------------------------------

## License

No license has been specified yet. Add a `LICENSE` file and update this
section if the project is intended to be distributed or reused under a
particular license.

