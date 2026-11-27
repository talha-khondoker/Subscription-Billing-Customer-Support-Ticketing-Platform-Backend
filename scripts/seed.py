# ----------------------------------------------------------------------
# scripts/seed.py
# Owner:   Member 6
# Purpose: Demo data so every role can log in on Day 1.
# ----------------------------------------------------------------------

"""Seed demo data so every role can log in and the demo story works. Owner: Member 6.
(Phase 1 + Phase 5 - replaces the Phase 1 file.)

Run from the project root:
    python -m scripts.seed                 # base data + demo activity
    python -m scripts.seed --no-activity   # only users, plans, SLA policies

Everyone logs in with the password below. Needs Member 1's app.core.security.hash_password.

DEMO ACTIVITY (relative to the moment you seed, so re-seed before each rehearsal):
  Acme Cloud (main demo organization)
    customer1  Pro (active): 3 paid invoices, one first discounted, one recovered after a failed attempt
    customer2  Basic (active): partial refund of 5.00, one overdue manual invoice (15.00 + tax)
    customer3  Business Yearly (active): paid yearly invoice
    customer4  Pro (active): latest renewal FAILED, 2 failed attempts, retry due now  <- demo story
    customer5  Basic CANCELLED 12 days ago (churn)
    7 tickets: a fresh HIGH payment ticket from customer4 (agent1), one escalated with a breached SLA,
    open / in progress / resolved / unassigned examples, internal notes, notifications, audit log entries
  Beta Analytics (second organization, lighter)
    customer3 has a PAST_DUE subscription (3 failed attempts), 2 tickets, customer4/5 have no subscription
"""
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.enums import (
    BillingPeriod, InvoiceItemType, InvoiceStatus, NotificationType, PaymentStatus, RefundStatus, Role,
    SubscriptionStatus, TicketCategory, TicketPriority, TicketStatus, AttemptStatus,
)
from app.core.security import hash_password
from app.models import (
    AuditLog, Customer, Invoice, InvoiceItem, Notification, Organization, Payment, PaymentAttempt, Plan,
    Refund, SlaPolicy, Subscription, Ticket, TicketMessage, User,
)
from app.utils.dates import utcnow
from app.utils.money import to_money

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
SLA_MINUTES = {priority: (first, resolution) for priority, first, resolution in SLA_DEFAULTS}

CUSTOMER_NAMES = ["Rahim Uddin", "Karim Hossain", "Nusrat Jahan", "Sadia Islam", "Tanvir Ahmed"]


def is_seeded(db) -> bool:
    return db.scalar(select(Organization.id).limit(1)) is not None


# =============================================================================== base data
def seed(db, with_activity: bool = True) -> dict:
    """Create everything and commit. Returns {slug: context} (handy for tests)."""
    password_hash = hash_password(DEFAULT_PASSWORD)  # hash once, reuse (bcrypt is slow)

    db.add(User(email="superadmin@subflow.test", password_hash=password_hash,
                full_name="Super Admin", role=Role.SUPER_ADMIN, organization_id=None))

    contexts = {}
    for org_data in ORGANIZATIONS:
        slug = org_data["slug"]
        org = Organization(name=org_data["name"])
        db.add(org)
        db.flush()

        admin = User(organization_id=org.id, email=f"admin@{slug}.test", password_hash=password_hash,
                     full_name=f"{org.name} Admin", role=Role.ORG_ADMIN)
        agents = [
            User(organization_id=org.id, email=f"agent{n}@{slug}.test", password_hash=password_hash,
                 full_name=f"{org.name} Agent {n}", role=Role.AGENT)
            for n in (1, 2)
        ]
        db.add_all([admin, *agents])
        db.flush()

        customers = []
        for n, name in enumerate(CUSTOMER_NAMES, start=1):
            customer_user = User(organization_id=org.id, email=f"customer{n}@{slug}.test",
                                 password_hash=password_hash, full_name=name, role=Role.CUSTOMER)
            db.add(customer_user)
            db.flush()
            customer = Customer(organization_id=org.id, user_id=customer_user.id,
                                phone=f"+88017000{n:05d}", company_name=f"{name.split()[0]} Traders")
            db.add(customer)
            db.flush()
            customers.append((customer_user, customer))

        plans = {}
        for name, description, price, period in PLANS:
            plan = Plan(organization_id=org.id, name=name, description=description, price=price,
                        billing_period=period, tax_percent=Decimal("5.00"))
            db.add(plan)
            plans[name] = plan

        policies = {}
        for priority, first_response, resolution in SLA_DEFAULTS:
            policy = SlaPolicy(organization_id=org.id, name=f"{priority.value.title()} priority",
                               priority=priority, first_response_minutes=first_response,
                               resolution_minutes=resolution)
            db.add(policy)
            policies[priority] = policy
        db.flush()

        contexts[slug] = dict(org=org, admin=admin, agents=agents, customers=customers,
                              plans=plans, policies=policies)

    if with_activity:
        seed_acme_activity(db, contexts["acme"])
        seed_beta_activity(db, contexts["beta"])

    db.commit()
    return contexts


# =============================================================================== activity helpers
class Activity:
    """Small builder that creates subscriptions, invoices, payments and tickets with past dates."""

    def __init__(self, db, ctx):
        self.db = db
        self.org = ctx["org"]
        self.admin = ctx["admin"]
        self.agents = ctx["agents"]
        self.customers = ctx["customers"]
        self.plans = ctx["plans"]
        self.policies = ctx["policies"]
        self.now = utcnow()
        self._invoice_seq = 0
        self._payment_seq = 0

    def at(self, **delta) -> datetime:
        return self.now - timedelta(**delta)

    # ---- billing
    def subscription(self, customer, plan, status, started_days_ago, period_start_days_ago, cancelled_days_ago=None):
        length = timedelta(days=365 if plan.billing_period == BillingPeriod.YEARLY else 30)
        start = self.at(days=started_days_ago)
        period_start = self.at(days=period_start_days_ago)
        sub = Subscription(
            organization_id=self.org.id, customer_id=customer.id, plan_id=plan.id, status=status,
            start_date=start, current_period_start=period_start, current_period_end=period_start + length,
            next_billing_date=None if status == SubscriptionStatus.CANCELLED else period_start + length,
            cancelled_at=self.at(days=cancelled_days_ago) if cancelled_days_ago is not None else None,
            created_at=start, updated_at=start,
        )
        self.db.add(sub)
        self.db.flush()
        return sub

    def invoice(self, customer, sub, plan, issued_days_ago, status, discount="0.00",
                paid_days_ago=None, due_in_days=7, price=None, label=None):
        issued = self.at(days=issued_days_ago)
        unit = Decimal(price) if price is not None else plan.price
        discount = Decimal(discount)
        tax = to_money((unit - discount) * plan.tax_percent / 100)
        paid_at = None
        if status in (InvoiceStatus.PAID, InvoiceStatus.REFUNDED):
            paid_at = self.at(days=paid_days_ago if paid_days_ago is not None else issued_days_ago)

        self._invoice_seq += 1
        invoice = Invoice(
            organization_id=self.org.id, customer_id=customer.id, subscription_id=sub.id,
            invoice_number=f"INV-{self.org.id}-{issued:%Y%m}-{self._invoice_seq:04d}",
            period_start=issued, period_end=issued + timedelta(days=365 if plan.billing_period == BillingPeriod.YEARLY else 30),
            subtotal=unit, discount_amount=discount, tax_amount=tax, total=to_money(unit - discount + tax),
            status=status, due_date=issued + timedelta(days=due_in_days), issued_at=issued, paid_at=paid_at,
            created_at=issued, updated_at=paid_at or issued,
        )
        invoice.items.append(InvoiceItem(
            item_type=InvoiceItemType.PLAN, description=label or f"{plan.name} plan ({plan.billing_period.value})",
            quantity=1, unit_amount=unit, amount=unit))
        if discount > 0:
            invoice.items.append(InvoiceItem(
                item_type=InvoiceItemType.DISCOUNT, description="Welcome discount",
                quantity=1, unit_amount=-discount, amount=-discount))
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def payment(self, invoice, status, attempts):
        """attempts: list of (when, ok, failure_reason, next_retry_at), oldest first."""
        self._payment_seq += 1
        last_reason = attempts[-1][2]
        payment = Payment(
            organization_id=self.org.id, invoice_id=invoice.id, customer_id=invoice.customer_id,
            amount=invoice.total, status=status, gateway_reference=f"mock_{self.org.id}_{self._payment_seq:04d}",
            failure_reason=last_reason if status == PaymentStatus.FAILED else None,
            created_at=attempts[0][0], updated_at=attempts[-1][0],
        )
        self.db.add(payment)
        self.db.flush()
        for number, (when, ok, reason, next_retry) in enumerate(attempts, start=1):
            self.db.add(PaymentAttempt(
                payment_id=payment.id, invoice_id=invoice.id, attempt_number=number,
                status=AttemptStatus.SUCCEEDED if ok else AttemptStatus.FAILED,
                gateway_response={"status": "succeeded"} if ok else {"status": "failed", "reason": reason},
                attempted_at=when, next_retry_at=next_retry,
            ))
        self.db.flush()
        return payment

    def paid(self, customer, sub, plan, issued_days_ago, **invoice_kwargs):
        """Shortcut: a PAID invoice with one successful payment attempt."""
        invoice = self.invoice(customer, sub, plan, issued_days_ago, InvoiceStatus.PAID, **invoice_kwargs)
        payment = self.payment(invoice, PaymentStatus.SUCCEEDED, [(invoice.paid_at, True, None, None)])
        return invoice, payment

    # ---- support
    def ticket(self, customer_pair, subject, description, category, priority, status, created_ago,
               agent=None, first_response_minutes=None, resolved_minutes=None, messages=()):
        _, customer = customer_pair
        created = self.now - created_ago
        first_due_minutes, resolution_due_minutes = SLA_MINUTES[priority]
        first_due = created + timedelta(minutes=first_due_minutes)
        resolution_due = created + timedelta(minutes=resolution_due_minutes)
        first_responded = created + timedelta(minutes=first_response_minutes) if first_response_minutes is not None else None
        resolved = created + timedelta(minutes=resolved_minutes) if resolved_minutes is not None else None
        finished = status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)

        ticket = Ticket(
            organization_id=self.org.id, customer_id=customer.id, subject=subject, description=description,
            category=category, priority=priority, status=status,
            assigned_agent_id=agent.id if agent else None, sla_policy_id=self.policies[priority].id,
            first_response_due=first_due, resolution_due=resolution_due,
            first_responded_at=first_responded, resolved_at=resolved,
            first_response_breached=(first_responded > first_due) if first_responded else (first_due < self.now and not finished),
            resolution_breached=(resolved > resolution_due) if resolved else (resolution_due < self.now and not finished),
            created_at=created, updated_at=resolved or first_responded or created,
        )
        self.db.add(ticket)
        self.db.flush()
        for sender, body, internal, minutes in messages:
            when = created + timedelta(minutes=minutes)
            self.db.add(TicketMessage(ticket_id=ticket.id, sender_id=sender.id, body=body,
                                      is_internal=internal, created_at=when, updated_at=when))
        self.db.flush()
        return ticket

    # ---- extras
    def notify(self, user, title, message, notif_type, is_read=False, minutes_ago=0):
        self.db.add(Notification(organization_id=self.org.id, user_id=user.id, title=title, message=message,
                                 type=notif_type, is_read=is_read, created_at=self.at(minutes=minutes_ago),
                                 updated_at=self.at(minutes=minutes_ago)))

    def audit(self, actor, action, entity_type, entity_id, old=None, new=None, days_ago=0):
        self.db.add(AuditLog(organization_id=self.org.id, actor_id=actor.id, action=action,
                             entity_type=entity_type, entity_id=entity_id, old_values=old, new_values=new,
                             created_at=self.at(days=days_ago), updated_at=self.at(days=days_ago)))


# =============================================================================== Acme (main demo)
def seed_acme_activity(db, ctx) -> None:
    a = Activity(db, ctx)
    pairs = a.customers
    (u1, c1), (u2, c2), (u3, c3), (u4, c4), (u5, c5) = pairs
    admin, (agent1, agent2) = a.admin, a.agents
    basic, pro, biz = a.plans["Basic"], a.plans["Pro"], a.plans["Business Yearly"]
    day = lambda n: a.at(days=n)

    # customer1: Pro, healthy; first invoice discounted; last invoice recovered after one failed attempt
    s1 = a.subscription(c1, pro, SubscriptionStatus.ACTIVE, started_days_ago=75, period_start_days_ago=15)
    a.paid(c1, s1, pro, 75, discount="3.00")
    a.paid(c1, s1, pro, 45)
    recovered = a.invoice(c1, s1, pro, 15, InvoiceStatus.PAID, paid_days_ago=14)
    a.payment(recovered, PaymentStatus.SUCCEEDED, [(day(15), False, "card_declined", day(14)), (day(14), True, None, None)])

    # customer2: Basic; partial refund; overdue manual invoice
    s2 = a.subscription(c2, basic, SubscriptionStatus.ACTIVE, started_days_ago=50, period_start_days_ago=20)
    a.paid(c2, s2, basic, 50)
    inv2, pay2 = a.paid(c2, s2, basic, 20)
    refund = Refund(organization_id=a.org.id, payment_id=pay2.id, invoice_id=inv2.id, amount=Decimal("5.00"),
                    reason="Goodwill credit for an outage", issued_by=admin.id, status=RefundStatus.COMPLETED,
                    created_at=day(18), updated_at=day(18))
    db.add(refund)
    a.invoice(c2, s2, basic, 8, InvoiceStatus.OPEN, price="15.00", label="Extra seats (manual invoice)", due_in_days=6)

    # customer3: Business Yearly
    s3 = a.subscription(c3, biz, SubscriptionStatus.ACTIVE, started_days_ago=120, period_start_days_ago=120)
    a.paid(c3, s3, biz, 120)

    # customer4: DEMO STORY - renewal failed twice, retry is due now
    s4 = a.subscription(c4, pro, SubscriptionStatus.ACTIVE, started_days_ago=34, period_start_days_ago=4)
    a.paid(c4, s4, pro, 34)
    failed_invoice = a.invoice(c4, s4, pro, 4, InvoiceStatus.FAILED)
    a.payment(failed_invoice, PaymentStatus.FAILED, [
        (day(4), False, "card_declined", day(3)),
        (day(3), False, "insufficient_funds", a.at(hours=1)),   # next retry already due
    ])

    # customer5: cancelled 12 days ago
    s5 = a.subscription(c5, basic, SubscriptionStatus.CANCELLED, started_days_ago=90, period_start_days_ago=60,
                        cancelled_days_ago=12)
    a.paid(c5, s5, basic, 90)
    a.paid(c5, s5, basic, 60)

    # ---- tickets
    t_story = a.ticket(pairs[3], "Payment failed but I was charged",
                       "My card shows a charge but my invoice is still unpaid.",
                       TicketCategory.PAYMENT, TicketPriority.HIGH, TicketStatus.OPEN,
                       created_ago=timedelta(minutes=5), agent=agent1)
    t_progress = a.ticket(pairs[0], "How do I switch to the yearly plan?",
                          "I would like to move from Pro to a yearly plan.",
                          TicketCategory.GENERAL, TicketPriority.MEDIUM, TicketStatus.IN_PROGRESS,
                          created_ago=timedelta(hours=3), agent=agent2, first_response_minutes=120,
                          messages=[(agent2, "Hi! You can switch from your dashboard. I will send the exact steps.", False, 120),
                                    (u1, "Thanks. Will the price change right away?", False, 150)])
    t_escalated = a.ticket(pairs[1], "Invoice shows the wrong tax amount",
                           "The tax on my last invoice looks too high.",
                           TicketCategory.BILLING, TicketPriority.HIGH, TicketStatus.ESCALATED,
                           created_ago=timedelta(hours=26), agent=agent1, first_response_minutes=30,
                           messages=[(agent1, "Checking your invoice now.", False, 30),
                                     (agent1, "Escalated: the tax rule needs an admin to check.", True, 90),
                                     (u2, "Any update on this?", False, 600)])
    a.ticket(pairs[2], "Please add invoice PDF download", "It would help our accounting team.",
             TicketCategory.GENERAL, TicketPriority.LOW, TicketStatus.RESOLVED,
             created_ago=timedelta(days=4), agent=agent2, first_response_minutes=120, resolved_minutes=40 * 60,
             messages=[(agent2, "Thanks for the idea, I passed it to the product team.", False, 120),
                       (agent2, "Marking this as resolved.", False, 40 * 60)])
    a.ticket(pairs[4], "I want to cancel my subscription", "Please cancel it at the end of the period.",
             TicketCategory.BILLING, TicketPriority.MEDIUM, TicketStatus.RESOLVED,
             created_ago=timedelta(days=13), agent=agent1, first_response_minutes=60, resolved_minutes=20 * 60,
             messages=[(agent1, "Done, your subscription is cancelled.", False, 20 * 60)])
    a.ticket(pairs[0], "Where can I find my last invoice?", "I cannot find the invoice PDF.",
             TicketCategory.BILLING, TicketPriority.MEDIUM, TicketStatus.RESOLVED,
             created_ago=timedelta(days=21), agent=agent2, first_response_minutes=60, resolved_minutes=600)
    a.ticket(pairs[1], "Feature request: dark mode", "Our team works at night.",
             TicketCategory.GENERAL, TicketPriority.LOW, TicketStatus.OPEN,
             created_ago=timedelta(hours=2), agent=None)           # unassigned

    # ---- notifications and audit log
    a.notify(agent1, f"New ticket #{t_story.id}", "High priority: Payment failed but I was charged", NotificationType.TICKET, minutes_ago=5)
    a.notify(agent2, f"Ticket #{t_progress.id} assigned to you", "How do I switch to the yearly plan?", NotificationType.TICKET, is_read=True, minutes_ago=180)
    a.notify(admin, f"SLA breach: ticket #{t_escalated.id}", "Missed its resolution deadline.", NotificationType.SLA, minutes_ago=60)
    a.notify(u4, "Payment failed", f"We could not charge invoice {failed_invoice.invoice_number}. We will retry.", NotificationType.PAYMENT, minutes_ago=60 * 24 * 3)
    db.flush()
    a.audit(admin, "refund.create", "refund", refund.id, new={"amount": "5.00"}, days_ago=18)
    a.audit(admin, "subscription.cancel", "subscription", s5.id, old={"status": "active"}, new={"status": "cancelled"}, days_ago=12)
    a.audit(agent1, "ticket.escalate", "ticket", t_escalated.id, old={"status": "open"}, new={"status": "escalated"}, days_ago=1)


# =============================================================================== Beta (lighter)
def seed_beta_activity(db, ctx) -> None:
    a = Activity(db, ctx)
    pairs = a.customers
    (u1, c1), (u2, c2), (u3, c3), _, _ = pairs
    agent1, agent2 = a.agents
    basic, pro = a.plans["Basic"], a.plans["Pro"]
    day = lambda n: a.at(days=n)

    s1 = a.subscription(c1, pro, SubscriptionStatus.ACTIVE, started_days_ago=40, period_start_days_ago=10)
    a.paid(c1, s1, pro, 40)
    a.paid(c1, s1, pro, 10)

    s2 = a.subscription(c2, basic, SubscriptionStatus.ACTIVE, started_days_ago=25, period_start_days_ago=25)
    a.paid(c2, s2, basic, 25)

    # customer3: past due after 3 failed attempts
    s3 = a.subscription(c3, pro, SubscriptionStatus.PAST_DUE, started_days_ago=70, period_start_days_ago=10)
    a.paid(c3, s3, pro, 70)
    a.paid(c3, s3, pro, 40)
    failed = a.invoice(c3, s3, pro, 10, InvoiceStatus.FAILED)
    a.payment(failed, PaymentStatus.FAILED, [
        (day(10), False, "card_declined", day(9)),
        (day(9), False, "card_declined", day(7)),
        (day(7), False, "card_expired", None),                  # last attempt, no more retries
    ])

    a.ticket(pairs[2], "Charged twice?", "I see two charges on my statement.",
             TicketCategory.PAYMENT, TicketPriority.HIGH, TicketStatus.IN_PROGRESS,
             created_ago=timedelta(days=1), agent=agent1, first_response_minutes=20,
             messages=[(agent1, "Looking into the payments now.", False, 20)])
    a.ticket(pairs[0], "Login problem", "I cannot log in on my phone.",
             TicketCategory.TECHNICAL, TicketPriority.MEDIUM, TicketStatus.RESOLVED,
             created_ago=timedelta(days=5), agent=agent2, first_response_minutes=45, resolved_minutes=300)


# =============================================================================== CLI
def main() -> None:
    with_activity = "--no-activity" not in sys.argv
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if is_seeded(db):
            print("Database already has data. Run scripts.reset_db to start fresh. Nothing changed.")
            return
        seed(db, with_activity=with_activity)
        print("Seed complete. Password for every account:", DEFAULT_PASSWORD)
        print("  superadmin@subflow.test")
        for org in ORGANIZATIONS:
            s = org["slug"]
            print(f"  {org['name']}: admin@{s}.test, agent1@{s}.test, agent2@{s}.test, customer1@{s}.test ... customer5@{s}.test")
        if with_activity:
            print("Demo story: log in as customer4@acme.test (failed renewal) and agent1@acme.test (open ticket).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
