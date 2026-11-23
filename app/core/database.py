# ----------------------------------------------------------------------
# app/core/database.py
# Owner: Shared (Member 1 owns; ask before changing)
# Purpose: Database engine, session factory, Base, get_db dependency.
# ----------------------------------------------------------------------
"""Database engine, session factory and the declarative Base used by every model."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

if settings.DATABASE_URL in {"sqlite://", "sqlite:///:memory:"}:
    _engine_options = {"poolclass": StaticPool}
elif ":6543/" in settings.DATABASE_URL:
    # Supabase transaction pooler (port 6543) handles pooling externally
    _engine_options = {"poolclass": NullPool}
else:
    _engine_options = {}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
    **_engine_options,
)

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
