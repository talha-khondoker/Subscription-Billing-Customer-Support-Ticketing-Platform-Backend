# ----------------------------------------------------------------------
# app/services/billing_context_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# Notes:
#   Flagship feature: the Billing-to-Ticket View.
# TODO:
#   - get_billing_context(db, ticket)  -> subscription, last 5 invoices, last 5 payments, failed attempts, refunds, last 5 tickets
