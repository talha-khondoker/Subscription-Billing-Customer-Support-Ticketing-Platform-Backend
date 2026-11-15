# ----------------------------------------------------------------------
# app/core/database.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Database engine, session factory, Base, get_db dependency.
# ----------------------------------------------------------------------
# TODO:
#   - create engine from DATABASE_URL (pool_pre_ping on; SQLite needs check_same_thread=False)
#   - SessionLocal factory
#   - declarative Base class
#   - get_db() generator dependency: open session, yield, always close
