"""End-to-end API flow: sign-up, profiles, plans, subscriptions, billing, tickets, dashboards, jobs.

Run from the project root:   pytest -q
Uses its own SQLite file (test_flow.db) and keeps the scheduler off.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_flow.db"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ENV"] = "development"

import pytest
from fastapi.testclient import TestClient

API = "/api/v1"
PW = "Secret123!"
S: dict = {}  # shared state between the ordered tests


@pytest.fixture(scope="module")
def client():
    from app.core.database import Base, SessionLocal, engine
    import app.models  # noqa: F401
    from app.core.enums import Role
    from app.core.security import hash_password
    from app.models import User
    from scripts.seed import seed

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed(db)  # demo data (Acme + Beta) incl. superadmin@subflow.test
    db.close()

    from app.main import app
    with TestClient(app) as c:
        yield c


def login(client, email, password=PW):
    r = client.post(f"{API}/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ok(r, code=200):
    assert r.status_code == code, f"{r.request.method} {r.request.url} -> {r.status_code}: {r.text}"
    return r.json()


# ------------------------------------------------------------------ sign-up and profiles
def test_organization_signup(client):
    r = client.post(f"{API}/auth/register-organization", json={
        "organization_name": "Zeta Corp", "admin_full_name": "Zed Admin",
        "admin_email": "zed@zeta.test", "admin_password": PW})
    user = ok(r, 201)
    assert user["role"] == "org_admin" and user["organization_id"]
    S["org_id"] = user["organization_id"]
    # duplicate organization / email give clean 409 errors
    r = client.post(f"{API}/auth/register-organization", json={
        "organization_name": "Zeta Corp", "admin_full_name": "X", "admin_email": "other@zeta.test",
        "admin_password": PW})
    assert r.status_code == 409 and r.json()["code"] == "ORGANIZATION_EXISTS"
    r = client.post(f"{API}/auth/register-organization", json={
        "organization_name": "Zeta Two", "admin_full_name": "X", "admin_email": "zed@zeta.test",
        "admin_password": PW})
    assert r.status_code == 409

    names = [o["name"] for o in ok(client.get(f"{API}/organizations/public"))]
    assert "Zeta Corp" in names and "Acme Cloud" in names

    S["admin"] = login(client, "zed@zeta.test")
    me = ok(client.get(f"{API}/organizations/me", headers=S["admin"]))
    assert me["name"] == "Zeta Corp"
    # default SLA policies were created
    policies = ok(client.get(f"{API}/sla-policies", headers=S["admin"]))
    assert sorted(p["priority"] for p in policies) == ["high", "low", "medium", "urgent"]


def test_customer_signup_and_profile(client):
    r = client.post(f"{API}/auth/register", json={
        "email": "cara@zeta.test", "password": PW, "full_name": "Cara Customer", "organization_id": S["org_id"]})
    assert ok(r, 201)["role"] == "customer"
    S["cust"] = login(client, "cara@zeta.test")

    prof = ok(client.get(f"{API}/customers/me", headers=S["cust"]))   # profile row exists right after sign-up
    assert prof["email"] == "cara@zeta.test"
    S["customer_id"] = prof["id"]
    prof = ok(client.patch(f"{API}/customers/me", headers=S["cust"],
                           json={"full_name": "Cara C.", "phone": "+8801700000000", "company_name": "Cara Ltd"}))
    assert prof["phone"] == "+8801700000000" and prof["full_name"] == "Cara C."
    assert ok(client.get(f"{API}/auth/me", headers=S["cust"]))["full_name"] == "Cara C."

    assert ok(client.patch(f"{API}/auth/me", headers=S["admin"], json={"full_name": "Zed Boss"}))["full_name"] == "Zed Boss"

    bad = client.post(f"{API}/auth/change-password", headers=S["cust"],
                      json={"current_password": "wrong", "new_password": "NewSecret123!"})
    assert bad.status_code == 400
    ok(client.post(f"{API}/auth/change-password", headers=S["cust"],
                   json={"current_password": PW, "new_password": "NewSecret123!"}))
    S["cust"] = login(client, "cara@zeta.test", "NewSecret123!")


def test_org_admin_edits_organization_and_agents(client):
    org = ok(client.patch(f"{API}/organizations/me", headers=S["admin"], json={"name": "Zeta Corporation"}))
    assert org["name"] == "Zeta Corporation"
    # a customer cannot edit the organization
    assert client.patch(f"{API}/organizations/me", headers=S["cust"], json={"name": "Hacked"}).status_code == 403

    agent = ok(client.post(f"{API}/users/agents", headers=S["admin"],
                           json={"email": "amy@zeta.test", "password": PW, "full_name": "Amy Agent"}), 201)
    S["agent_id"] = agent["id"]
    S["agent"] = login(client, "amy@zeta.test")
    assert len(ok(client.get(f"{API}/users/agents", headers=S["admin"]))) >= 1
    upd = ok(client.patch(f"{API}/users/{agent['id']}", headers=S["admin"], json={"full_name": "Amy A."}))
    assert upd["full_name"] == "Amy A."
    # org admins cannot be edited through the agent endpoint
    me_id = ok(client.get(f"{API}/auth/me", headers=S["admin"]))["id"]
    assert client.patch(f"{API}/users/{me_id}", headers=S["admin"], json={"is_active": False}).status_code == 400


# ------------------------------------------------------------------ plans and subscriptions
def test_plans(client):
    p1 = ok(client.post(f"{API}/plans", headers=S["admin"], json={
        "name": "Starter", "description": "d", "price": "29.00", "billing_period": "monthly", "tax_percent": "5.00"}), 201)
    p2 = ok(client.post(f"{API}/plans", headers=S["admin"], json={
        "name": "Yearly", "price": "290.00", "billing_period": "yearly", "tax_percent": "5.00"}), 201)
    p3 = ok(client.post(f"{API}/plans", headers=S["admin"], json={
        "name": "Pro", "price": "59.00", "billing_period": "monthly"}), 201)
    S.update(p1=p1["id"], p2=p2["id"], p3=p3["id"])
    assert client.post(f"{API}/plans", headers=S["admin"], json={
        "name": "Starter", "price": "1.00", "billing_period": "monthly"}).status_code == 409
    assert client.post(f"{API}/plans", headers=S["cust"], json={
        "name": "Mine", "price": "1.00", "billing_period": "monthly"}).status_code == 403

    ok(client.patch(f"{API}/plans/{p3['id']}", headers=S["admin"], json={"is_active": False}))
    assert len(ok(client.get(f"{API}/plans", headers=S["admin"]))) == 3          # admin sees all
    assert len(ok(client.get(f"{API}/plans", headers=S["cust"]))) == 2           # customer: active only
    assert len(ok(client.get(f"{API}/plans", headers=S["agent"]))) == 2          # agent: active only
    # nobody can reach another organization's plans
    ok(client.post(f"{API}/auth/register-organization", json={
        "organization_name": "Other Org", "admin_full_name": "O", "admin_email": "o@other.test", "admin_password": PW}), 201)
    other = login(client, "o@other.test")
    assert ok(client.get(f"{API}/plans", headers=other)) == []
    assert client.patch(f"{API}/plans/{p1['id']}", headers=other, json={"name": "Stolen"}).status_code == 404


def test_subscribe_and_billing(client):
    sub = ok(client.post(f"{API}/subscriptions", headers=S["cust"], json={"plan_id": S["p1"]}), 201)
    assert sub["status"] == "active" and sub["plan_name"] == "Starter" and sub["customer_name"] == "Cara C."
    S["sub1"] = sub["id"]
    assert client.post(f"{API}/subscriptions", headers=S["cust"], json={"plan_id": S["p1"]}).status_code == 409

    invs = ok(client.get(f"{API}/invoices/me", headers=S["cust"]))
    assert invs["total"] == 1
    inv = invs["items"][0]
    assert inv["status"] == "paid" and float(inv["total"]) == 30.45   # 29.00 + 5% tax
    detail = ok(client.get(f"{API}/invoices/{inv['id']}", headers=S["cust"]))
    assert len(detail["items"]) == 1 and float(detail["tax_amount"]) == 1.45
    pays = ok(client.get(f"{API}/payments/me", headers=S["cust"]))
    assert pays["items"][0]["status"] == "succeeded"
    S["pay1"] = pays["items"][0]["id"]
    attempts = ok(client.get(f"{API}/payments/{S['pay1']}/attempts", headers=S["cust"]))
    assert attempts[0]["attempt_number"] == 1

    unread = ok(client.get(f"{API}/notifications/unread-count", headers=S["cust"]))["unread_count"]
    assert unread >= 2   # subscription started + payment received
    notes = ok(client.get(f"{API}/notifications", headers=S["cust"]))
    assert notes["unread_count"] == unread and notes["items"]
    ok(client.post(f"{API}/notifications/read-all", headers=S["cust"]))
    assert ok(client.get(f"{API}/notifications/unread-count", headers=S["cust"]))["unread_count"] == 0
    # org admin was told about the new subscription
    assert any(n["title"] == "New subscription" for n in ok(client.get(f"{API}/notifications", headers=S["admin"]))["items"])


def test_change_plan_pause_resume_cancel(client):
    # monthly -> yearly: different billing period, new period starts now, proration invoice is charged
    sub = ok(client.post(f"{API}/subscriptions/{S['sub1']}/change-plan", headers=S["cust"], json={"new_plan_id": S["p2"]}))
    assert sub["plan_name"] == "Yearly" and sub["billing_period"] == "yearly"
    invs = ok(client.get(f"{API}/invoices/me", headers=S["cust"]))
    assert invs["total"] == 2 and invs["items"][0]["status"] == "paid" and float(invs["items"][0]["total"]) > 0
    # yearly -> monthly: net credit is recorded as a settled credit invoice
    sub = ok(client.post(f"{API}/subscriptions/{S['sub1']}/change-plan", headers=S["cust"], json={"new_plan_id": S["p1"]}))
    assert sub["plan_name"] == "Starter"
    totals = [float(i["total"]) for i in ok(client.get(f"{API}/invoices/me", headers=S["cust"]))["items"]]
    assert any(t < 0 for t in totals)
    assert client.post(f"{API}/subscriptions/{S['sub1']}/change-plan", headers=S["cust"],
                       json={"new_plan_id": S["p1"]}).status_code == 400            # same plan

    # pause / resume
    assert ok(client.post(f"{API}/subscriptions/{S['sub1']}/pause", headers=S["cust"]))["status"] == "paused"
    assert client.post(f"{API}/subscriptions/{S['sub1']}/pause", headers=S["cust"]).status_code == 400
    assert ok(client.post(f"{API}/subscriptions/{S['sub1']}/resume", headers=S["cust"]))["status"] == "active"

    # another customer cannot touch this subscription
    ok(client.post(f"{API}/auth/register", json={"email": "dan@zeta.test", "password": PW, "full_name": "Dan",
                                                 "organization_id": S["org_id"]}), 201)
    dan = login(client, "dan@zeta.test")
    assert client.post(f"{API}/subscriptions/{S['sub1']}/pause", headers=dan).status_code == 404
    assert client.post(f"{API}/subscriptions/{S['sub1']}/cancel", headers=dan).status_code == 404
    assert client.get(f"{API}/subscriptions", headers=S["cust"]).status_code == 403    # staff only

    # cancel at period end (customer)
    sub = ok(client.post(f"{API}/subscriptions/{S['sub1']}/cancel", headers=S["cust"], json={"at_period_end": True}))
    assert sub["status"] == "active" and sub["cancel_at_period_end"] is True

    # org admin cancels a second subscription immediately and sees customer names
    sub2 = ok(client.post(f"{API}/subscriptions", headers=S["cust"], json={"plan_id": S["p2"]}), 201)
    listed = ok(client.get(f"{API}/subscriptions", headers=S["admin"]))
    assert all(s["customer_name"] for s in listed) and len(listed) == 2
    assert len(ok(client.get(f"{API}/subscriptions?subscription_status=active", headers=S["agent"]))) == 2
    done = ok(client.post(f"{API}/subscriptions/{sub2['id']}/cancel", headers=S["admin"], json={"at_period_end": False}))
    assert done["status"] == "cancelled" and done["cancelled_at"]


def test_failed_payment_retry_and_manual_pay(client):
    ok(client.put(f"{API}/gateway/mock-config", headers=S["admin"], json={"mode": "always_fail"}))
    sub = ok(client.post(f"{API}/subscriptions", headers=S["cust"], json={"plan_id": S["p2"]}), 201)
    invs = ok(client.get(f"{API}/invoices/me?status=failed", headers=S["cust"]))
    assert invs["total"] == 1
    S["failed_invoice"] = invs["items"][0]["id"]
    pays = ok(client.get(f"{API}/payments/me?status=failed", headers=S["cust"]))
    pid = pays["items"][0]["id"]
    attempts = ok(client.get(f"{API}/payments/{pid}/attempts", headers=S["cust"]))
    assert attempts[0]["status"] == "failed" and attempts[0]["next_retry_at"]
    assert any(n["title"] == "Payment failed" for n in ok(client.get(f"{API}/notifications", headers=S["cust"]))["items"])

    # customer pays the failed invoice manually once the gateway works again
    ok(client.put(f"{API}/gateway/mock-config", headers=S["admin"], json={"mode": "always_success"}))
    paid = ok(client.post(f"{API}/invoices/{S['failed_invoice']}/pay", headers=S["cust"]))
    assert paid["status"] == "succeeded"
    assert ok(client.get(f"{API}/invoices/{S['failed_invoice']}", headers=S["cust"]))["status"] == "paid"
    # cannot pay twice, cannot pay someone else's invoice
    assert client.post(f"{API}/invoices/{S['failed_invoice']}/pay", headers=S["cust"]).status_code == 409
    dan = login(client, "dan@zeta.test")
    assert client.post(f"{API}/invoices/{S['failed_invoice']}/pay", headers=dan).status_code == 404
    assert client.get(f"{API}/invoices/{S['failed_invoice']}", headers=dan).status_code == 404


def test_refunds(client):
    assert client.post(f"{API}/payments/{S['pay1']}/refund", headers=S["cust"], json={"amount": "1.00"}).status_code == 403
    r = ok(client.post(f"{API}/payments/{S['pay1']}/refund", headers=S["admin"], json={"amount": "10.00", "reason": "goodwill"}))
    assert r["status"] == "completed"
    assert client.post(f"{API}/payments/{S['pay1']}/refund", headers=S["admin"], json={"amount": "100.00"}).status_code == 409
    assert ok(client.post(f"{API}/payments/{S['pay1']}/refund", headers=S["admin"], json={"amount": "20.45"}))["amount"]
    assert ok(client.get(f"{API}/refunds", headers=S["admin"]))["total"] == 2
    pays = ok(client.get(f"{API}/payments?status=refunded", headers=S["admin"]))
    assert pays["total"] == 1


# ------------------------------------------------------------------ tickets
def test_ticket_workflow(client):
    t = ok(client.post(f"{API}/tickets", headers=S["cust"], json={
        "subject": "Need help", "description": "Please help", "category": "billing", "priority": "high"}), 201)
    tid = t["id"]
    assert t["assigned_agent_name"] and t["first_response_due"] and t["status"] == "open"
    assert t["first_response_remaining_seconds"] is not None

    # agent works the ticket
    assert tid in [x["id"] for x in ok(client.get(f"{API}/tickets", headers=S["agent"]))["items"]]
    ok(client.post(f"{API}/tickets/{tid}/messages", headers=S["agent"], json={"body": "Hello, looking now"}), 201)
    ok(client.post(f"{API}/tickets/{tid}/notes", headers=S["agent"], json={"body": "internal: check refunds"}), 201)
    cust_view = ok(client.get(f"{API}/tickets/{tid}", headers=S["cust"]))
    assert all(not m["is_internal"] for m in cust_view["messages"]) and len(cust_view["messages"]) == 1
    staff_view = ok(client.get(f"{API}/tickets/{tid}", headers=S["admin"]))
    assert len(staff_view["messages"]) == 2 and staff_view["status"] == "in_progress"
    assert staff_view["first_responded_at"]

    ctx = ok(client.get(f"{API}/tickets/{tid}/billing-context", headers=S["agent"]))
    assert ctx["customer"]["email"] == "cara@zeta.test" and ctx["subscription"] and ctx["invoices"]
    assert client.get(f"{API}/tickets/{tid}/billing-context", headers=S["cust"]).status_code == 403

    # allowed / forbidden status moves
    assert ok(client.patch(f"{API}/tickets/{tid}", headers=S["agent"], json={"status": "waiting_customer"}))["status"] == "waiting_customer"
    assert client.patch(f"{API}/tickets/{tid}", headers=S["agent"], json={"status": "resolved"}).status_code == 400
    ok(client.post(f"{API}/tickets/{tid}/messages", headers=S["cust"], json={"body": "Thanks, any news?"}), 201)
    assert ok(client.get(f"{API}/tickets/{tid}", headers=S["cust"]))["status"] == "in_progress"
    assert ok(client.patch(f"{API}/tickets/{tid}", headers=S["agent"], json={"priority": "urgent"}))["priority"] == "urgent"

    # org admin: can only add notes (no public reply), can assign, cannot escalate
    assert client.post(f"{API}/tickets/{tid}/messages", headers=S["admin"], json={"body": "hi"}).status_code == 403
    ok(client.post(f"{API}/tickets/{tid}/notes", headers=S["admin"], json={"body": "admin note"}), 201)
    bob = ok(client.post(f"{API}/users/agents", headers=S["admin"],
                         json={"email": "bob@zeta.test", "password": PW, "full_name": "Bob Agent"}), 201)
    ok(client.post(f"{API}/tickets/{tid}/assign", headers=S["admin"], json={"agent_id": bob["id"]}))      # reassign
    assert tid not in [x["id"] for x in ok(client.get(f"{API}/tickets", headers=S["agent"]))["items"]]   # amy lost it
    ok(client.post(f"{API}/tickets/{tid}/assign", headers=S["admin"], json={"agent_id": S["agent_id"]}))  # and back
    assert client.post(f"{API}/tickets/{tid}/escalate", headers=S["admin"]).status_code == 403
    assert ok(client.post(f"{API}/tickets/{tid}/escalate", headers=S["agent"], json={"reason": "need admin"}))["status"] == "escalated"
    assert ok(client.patch(f"{API}/tickets/{tid}", headers=S["agent"], json={"status": "in_progress"}))["status"] == "in_progress"

    # resolve, then the customer can reopen by replying
    assert ok(client.post(f"{API}/tickets/{tid}/resolve", headers=S["agent"], json={"note": "All fixed"}))["status"] == "resolved"
    ok(client.post(f"{API}/tickets/{tid}/messages", headers=S["cust"], json={"body": "Still broken"}), 201)
    assert ok(client.get(f"{API}/tickets/{tid}", headers=S["cust"]))["status"] == "open"
    assert ok(client.post(f"{API}/tickets/{tid}/resolve", headers=S["admin"]))["status"] == "resolved"

    # filters / visibility
    assert ok(client.get(f"{API}/tickets?status=resolved&search=help", headers=S["admin"]))["total"] == 1
    dan = login(client, "dan@zeta.test")
    assert client.get(f"{API}/tickets/{tid}", headers=dan).status_code == 404
    assert any("New ticket" in n["title"] for n in ok(client.get(f"{API}/notifications", headers=S["agent"]))["items"])


# ------------------------------------------------------------------ customers, dashboards, audit, jobs
def test_customers_admin_view_and_edit(client):
    lst = ok(client.get(f"{API}/customers?search=cara", headers=S["admin"]))
    assert lst["total"] == 1
    cid = S["customer_id"]
    detail = ok(client.get(f"{API}/customers/{cid}", headers=S["agent"]))
    assert detail["subscriptions"] and detail["invoices"] and detail["payments"] and detail["tickets"]
    edited = ok(client.patch(f"{API}/customers/{cid}", headers=S["admin"], json={"phone": "+111", "company_name": "Edited"}))
    assert edited["phone"] == "+111"
    assert client.patch(f"{API}/customers/{cid}", headers=S["agent"], json={"phone": "x"}).status_code == 403
    # deactivate Dan's login
    dan_id = ok(client.get(f"{API}/customers?search=dan", headers=S["admin"]))["items"][0]["id"]
    assert ok(client.patch(f"{API}/customers/{dan_id}", headers=S["admin"], json={"is_active": False}))["is_active"] is False
    r = client.post(f"{API}/auth/login", data={"username": "dan@zeta.test", "password": PW})
    assert r.status_code == 401


def test_dashboards_audit_and_jobs_for_new_org(client):
    adm = ok(client.get(f"{API}/dashboard/admin?days=30", headers=S["admin"]))
    assert float(adm["revenue"]["mrr"]) > 0 and adm["subscriptions"]["active"] >= 1
    assert adm["tickets"]["open"] >= 0
    ag = ok(client.get(f"{API}/dashboard/agent?days=30", headers=S["agent"]))
    assert "needs_attention" in ag
    cu = ok(client.get(f"{API}/dashboard/customer", headers=S["cust"]))
    assert cu["subscription"] and cu["recent_invoices"]
    assert client.get(f"{API}/dashboard/admin", headers=S["cust"]).status_code == 403

    logs = ok(client.get(f"{API}/audit-logs?page_size=100", headers=S["admin"]))
    actions = {l["action"] for l in logs["items"]}
    assert {"plan.create", "subscription.create", "subscription.cancel", "subscription.change_plan",
            "payment.refund", "ticket.assign", "ticket.escalate", "ticket.resolve", "organization.update",
            "customer.update"} <= actions, actions
    assert all(l["actor_name"] for l in logs["items"] if l["actor_id"])

    for job in ("run-renewals", "run-retries", "run-sla-check"):
        ok(client.post(f"{API}/admin/jobs/{job}", headers=S["admin"]))
    assert client.post(f"{API}/admin/jobs/run-renewals", headers=S["cust"]).status_code == 403


def test_super_admin_and_seed_data(client):
    sa = login(client, "superadmin@subflow.test", "Password123!")
    plat = ok(client.get(f"{API}/dashboard/platform", headers=sa))
    assert plat["organizations_total"] >= 4
    orgs = ok(client.get(f"{API}/organizations", headers=sa))
    zeta = next(o for o in orgs["items"] if o["name"] == "Zeta Corporation")
    assert ok(client.patch(f"{API}/organizations/{zeta['id']}", headers=sa, json={"status": "disabled"}))["status"] == "disabled"
    assert client.get(f"{API}/plans", headers=S["admin"]).status_code == 403          # disabled org is locked out
    ok(client.patch(f"{API}/organizations/{zeta['id']}", headers=sa, json={"status": "active"}))
    assert ok(client.get(f"{API}/audit-logs", headers=sa))["total"] > 0
    assert client.get(f"{API}/dashboard/platform", headers=S["admin"]).status_code == 403
    new_org = ok(client.post(f"{API}/organizations", headers=sa, json={
        "name": "Made By SA", "admin_email": "sa-made@x.test", "admin_password": PW, "admin_full_name": "Made"}), 201)
    assert new_org["name"] == "Made By SA"

    # seeded Acme accounts work end-to-end
    admin = login(client, "admin@acme.test", "Password123!")
    agent1 = login(client, "agent1@acme.test", "Password123!")
    cust4 = login(client, "customer4@acme.test", "Password123!")
    for hdr, path in [(admin, "admin"), (agent1, "agent"), (cust4, "customer")]:
        ok(client.get(f"{API}/dashboard/{path}", headers=hdr))
    tickets = ok(client.get(f"{API}/tickets", headers=agent1))
    assert tickets["total"] >= 1
    story = next(t for t in ok(client.get(f"{API}/tickets?search=Payment failed", headers=agent1))["items"])
    ctx = ok(client.get(f"{API}/tickets/{story['id']}/billing-context", headers=agent1))
    assert ctx["failed_attempt_count"] >= 2 and ctx["alerts"]
    # the demo retry is due: run-retries succeeds the payment (mock gateway is on "always_success")
    res = ok(client.post(f"{API}/admin/jobs/run-retries", headers=admin))
    assert res["retried"] >= 1
    assert ok(client.get(f"{API}/dashboard/customer", headers=cust4))["has_failed_payment"] is False
    ok(client.post(f"{API}/admin/jobs/run-sla-check", headers=admin))
    assert ok(client.get(f"{API}/customers", headers=agent1))["total"] == 5
    assert client.get(f"{API}/customers", headers=cust4).status_code == 403
