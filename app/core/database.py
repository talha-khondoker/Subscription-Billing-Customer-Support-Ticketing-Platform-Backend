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

"""Database engine, session factory and the declarative Base used by every model."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Parent class of all SQLAlchemy models."""


def get_db():
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

