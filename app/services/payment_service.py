# ----------------------------------------------------------------------
# app/services/payment_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - attempt_payment(db, invoice)  -> creates payment + attempt 1 via mock_gateway
#   - pay_invoice(db, customer, invoice_id)
#   - list_payments(db, user, filters, page)
#   - get_attempts(db, payment_id)
#   - on success: invoice paid; on failure: store reason and ask retry_service for next time
