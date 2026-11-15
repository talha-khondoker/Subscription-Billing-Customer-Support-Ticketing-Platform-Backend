# ----------------------------------------------------------------------
# app/services/retry_service.py
# Owner:   Member 4
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - schedule_next_retry(db, payment)  -> uses RETRY_SCHEDULE_DAYS
#   - run_due_retries(db)  -> retry payments whose next_retry_at has passed
#   - after MAX_RETRY_ATTEMPTS failures: subscription past_due + notify admin
