
# Called by routers and jobs.


from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.core.enums import InvoiceStatus, InvoiceItemType, Role
from app.core.tenancy import scoped
from app.models.invoice import Invoice, InvoiceItem
from app.models.subscription import Subscription
from app.schemas.invoice import InvoiceFilter
from app.utils.dates import utcnow


# Money calculation helper
def _money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# Generate unique invoice number for an organization and month
def _generate_invoice_number(db, organization_id, issued_at):
    year_month = issued_at.strftime("%Y%m")

    prefix = f"INV-{organization_id}-{year_month}-"

    last_invoice = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.invoice_number.like(f"{prefix}%")
        )
        .order_by(Invoice.id.desc())
        .first()
    )

    if last_invoice:
        last_sequence = int(last_invoice.invoice_number.split("-")[-1])
        sequence = last_sequence + 1
    else:
        sequence = 1

    return f"{prefix}{sequence:04d}"


# Recalculate subtotal, tax and total
def recalculate_totals(invoice):
    subtotal = sum(
        (Decimal(str(item.amount)) for item in invoice.items),
        Decimal("0.00")
    )

    discount = Decimal(str(invoice.discount_amount or 0))

    tax_percent = Decimal("0.00")

    if invoice.subscription and invoice.subscription.plan:
        tax_percent = Decimal(
            str(invoice.subscription.plan.tax_percent or 0)
        )

    taxable_amount = subtotal - discount

    tax = taxable_amount * tax_percent / Decimal("100")
    tax = _money(tax)

    total = _money(taxable_amount + tax)

    invoice.subtotal = _money(subtotal)
    invoice.discount_amount = _money(discount)
    invoice.tax_amount = tax
    invoice.total = total

    return invoice


# Generate first or renewal invoice for a subscription
def generate_for_subscription(db, subscription):
    issued_at = utcnow()

    plan = subscription.plan

    invoice_number = _generate_invoice_number(
        db,
        subscription.organization_id,
        issued_at
    )

    invoice = Invoice(
        organization_id=subscription.organization_id,
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        invoice_number=invoice_number,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        subtotal=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total=Decimal("0.00"),
        status=InvoiceStatus.OPEN,
        issued_at=issued_at
    )

    plan_item = InvoiceItem(
        item_type=InvoiceItemType.PLAN,
        description=f"{plan.name} subscription",
        quantity=1,
        unit_amount=_money(plan.price),
        amount=_money(plan.price)
    )

    invoice.items.append(plan_item)

    recalculate_totals(invoice)

    db.add(invoice)
    db.flush()

    return (
        invoice.items,
        invoice.tax_amount,
        invoice.discount_amount,
        invoice.total,
        invoice.invoice_number
    )


# Build an invoice for a mid-period plan change
def build_proration_invoice(db, subscription, amount):
    issued_at = utcnow()

    proration_amount = _money(amount)

    invoice_number = _generate_invoice_number(
        db,
        subscription.organization_id,
        issued_at
    )

    invoice = Invoice(
        organization_id=subscription.organization_id,
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        invoice_number=invoice_number,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        subtotal=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total=Decimal("0.00"),
        status=InvoiceStatus.OPEN,
        issued_at=issued_at
    )

    proration_item = InvoiceItem(
        item_type=InvoiceItemType.PRORATION,
        description="Plan change proration adjustment",
        quantity=1,
        unit_amount=proration_amount,
        amount=proration_amount
    )

    invoice.items.append(proration_item)

    recalculate_totals(invoice)

    db.add(invoice)
    db.flush()

    return invoice


# Get one invoice with organization and customer access control
def get_invoice(db, user, invoice_id):
    query = scoped(db.query(Invoice), Invoice, user)

    if user.role == Role.CUSTOMER:
        customer = getattr(user, "customer_profile", None)

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )

        query = query.filter(
            Invoice.customer_id == customer.id
        )

    invoice = query.filter(
        Invoice.id == invoice_id
    ).first()

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    return invoice


# List invoices with filters and pagination
def list_invoices(db, user, filters: InvoiceFilter, page=None):
    query = scoped(db.query(Invoice), Invoice, user)

    if user.role == Role.CUSTOMER:
        customer = getattr(user, "customer_profile", None)

        if customer is None:
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": filters.page_size
            }

        query = query.filter(
            Invoice.customer_id == customer.id
        )

    if filters.customer_id is not None:
        query = query.filter(
            Invoice.customer_id == filters.customer_id
        )

    if filters.status is not None:
        query = query.filter(
            Invoice.status == filters.status
        )

    if filters.date_from is not None:
        query = query.filter(
            Invoice.issued_at >= filters.date_from
        )

    if filters.date_to is not None:
        query = query.filter(
            Invoice.issued_at <= filters.date_to
        )

    total = query.count()

    current_page = page if page is not None else filters.page
    page_size = filters.page_size

    invoices = (
        query
        .order_by(Invoice.issued_at.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": invoices,
        "total": total,
        "page": current_page,
        "page_size": page_size
    }