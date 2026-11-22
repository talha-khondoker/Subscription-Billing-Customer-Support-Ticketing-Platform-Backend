# ----------------------------------------------------------------------
# app/jobs/renewal_job.py
# Owner:   Member 4
# Purpose: Renew subscriptions that are due.
# ----------------------------------------------------------------------
# TODO:
#   - find active subscriptions with next_billing_date <= now
#   - call subscription_service.renew and payment_service.attempt_payment
#   - also callable from POST /admin/jobs/run-renewals

"""Run due renewals in a short lived database session."""
import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.services import payment_service, subscription_service
from app.utils.dates import utcnow

logger = logging.getLogger("subflow.jobs.renewal")


def run_renewals(organization_id: int | None = None) -> dict[str, int]:
    db = SessionLocal()
    try:
        renew = getattr(subscription_service, "renew", None)
        if renew is None:
            logger.warning("Renewal skipped: subscription_service.renew is not implemented")
            return {"renewed": 0, "skipped": 1}
        query = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.next_billing_date.is_not(None),
            Subscription.next_billing_date <= utcnow(),
        )
        if organization_id is not None:
            query = query.where(Subscription.organization_id == organization_id)
        due = db.scalars(query.order_by(Subscription.next_billing_date, Subscription.id)).all()
        renewed = 0
        for subscription in due:
            invoice = renew(db, subscription)
            if invoice is not None:
                payment_service.attempt_payment(db, invoice)
            renewed += 1
        return {"renewed": renewed}
    except Exception:
        db.rollback()
        logger.exception("Subscription renewal cycle failed")
        raise
    finally:
        db.close()
