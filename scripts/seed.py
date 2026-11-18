# ----------------------------------------------------------------------
# scripts/seed.py
# Owner:   Member 6
# Purpose: Demo data so every role can log in on Day 1.
# ----------------------------------------------------------------------
# TODO:
#   - 1 Super Admin
#   - 2 organizations, each with 1 Org Admin and 2 agents
#   - 5 customers per organization
#   - 3 plans per organization
#   - default SLA policies
#   - sample subscriptions, invoices, payments (some failed), tickets

"""Seed demo data so every role can log in on Day 1. Owner: Member 6.

Run from the project root:   python -m scripts.seed

First version creates: 1 Super Admin, 2 organizations (each with 1 Org Admin, 2 agents,
5 customers, 3 plans, 4 SLA policies). Everyone logs in with the password below.

LATER (Phase 5): add subscriptions, invoices, payments (some failed), tickets.
Needs from Member 1: app.core.security.hash_password.
"""
from decimal import Decimal

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.enums import BillingPeriod, Role, TicketPriority
from app.core.security import hash_password
from app.models import Customer, Organization, Plan, SlaPolicy, User

DEFAULT_PASSWORD = "Password123!"

ORGANIZATIONS = [
    {"name": "Acme Cloud", "slug": "acme"},
    {"name": "Beta Analytics", "slug": "beta"},
]

PLANS = [
    ("Basic", "For individuals", Decimal("10.00"), BillingPeriod.MONTHLY),
    ("Pro", "For small teams", Decimal("29.00"), BillingPeriod.MONTHLY),
    ("Business Yearly", "For companies, billed yearly", Decimal("290.00"), BillingPeriod.YEARLY),
]

# priority, first response minutes, resolution minutes
SLA_DEFAULTS = [
    (TicketPriority.URGENT, 15, 4 * 60),
    (TicketPriority.HIGH, 60, 8 * 60),
    (TicketPriority.MEDIUM, 4 * 60, 24 * 60),
    (TicketPriority.LOW, 8 * 60, 72 * 60),
]

CUSTOMER_NAMES = ["Rahim Uddin", "Karim Hossain", "Nusrat Jahan", "Sadia Islam", "Tanvir Ahmed"]


def seed(db) -> None:
    password_hash = hash_password(DEFAULT_PASSWORD)  # hash once, reuse (bcrypt is slow)

    db.add(User(email="superadmin@subflow.test", password_hash=password_hash,
                full_name="Super Admin", role=Role.SUPER_ADMIN, organization_id=None))

    for org_data in ORGANIZATIONS:
        slug = org_data["slug"]
        org = Organization(name=org_data["name"])
        db.add(org)
        db.flush()

        db.add(User(organization_id=org.id, email=f"admin@{slug}.test", password_hash=password_hash,
                    full_name=f"{org.name} Admin", role=Role.ORG_ADMIN))
        for n in (1, 2):
            db.add(User(organization_id=org.id, email=f"agent{n}@{slug}.test", password_hash=password_hash,
                        full_name=f"{org.name} Agent {n}", role=Role.AGENT))

        for n, name in enumerate(CUSTOMER_NAMES, start=1):
            customer_user = User(organization_id=org.id, email=f"customer{n}@{slug}.test",
                                 password_hash=password_hash, full_name=name, role=Role.CUSTOMER)
            db.add(customer_user)
            db.flush()
            db.add(Customer(organization_id=org.id, user_id=customer_user.id,
                            phone=f"+88017000{n:05d}", company_name=f"{name.split()[0]} Traders"))

        for name, description, price, period in PLANS:
            db.add(Plan(organization_id=org.id, name=name, description=description, price=price,
                        billing_period=period, tax_percent=Decimal("5.00")))

        for priority, first_response, resolution in SLA_DEFAULTS:
            db.add(SlaPolicy(organization_id=org.id, name=f"{priority.value.title()} priority",
                             priority=priority, first_response_minutes=first_response,
                             resolution_minutes=resolution))

        db.flush()

    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Organization.id).limit(1)) is not None:
            print("Database already has data. Run scripts.reset_db to start fresh. Nothing changed.")
            return
        seed(db)
        print("Seed complete. Password for every account:", DEFAULT_PASSWORD)
        print("  superadmin@subflow.test")
        for org in ORGANIZATIONS:
            s = org["slug"]
            print(f"  {org['name']}: admin@{s}.test, agent1@{s}.test, agent2@{s}.test, customer1@{s}.test ... customer5@{s}.test")
    finally:
        db.close()


if __name__ == "__main__":
    main()
