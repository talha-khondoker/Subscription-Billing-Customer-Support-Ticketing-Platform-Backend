# ----------------------------------------------------------------------
# app/services/ticket_service.py
# Owner:   Member 5
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - create_ticket(db, customer, data)  -> sla_service + assignment_service
#   - list_tickets(db, user, filters, page)
#   - get_ticket(db, user, id)  -> hide internal notes from customers
#   - update_ticket
#   - assign_ticket
#   - add_message  (agent reply sets first_responded_at)
#   - add_internal_note
#   - escalate_ticket
#   - resolve_ticket
