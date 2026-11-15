# ----------------------------------------------------------------------
# app/jobs/renewal_job.py
# Owner:   Member 4
# Purpose: Renew subscriptions that are due.
# ----------------------------------------------------------------------
# TODO:
#   - find active subscriptions with next_billing_date <= now
#   - call subscription_service.renew and payment_service.attempt_payment
#   - also callable from POST /admin/jobs/run-renewals
