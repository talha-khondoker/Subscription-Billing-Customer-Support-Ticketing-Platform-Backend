# ----------------------------------------------------------------------
# scripts/create_tables.py
# Owner:   Member 1
# Purpose: Create all tables from the models.
# ----------------------------------------------------------------------
# TODO:
#   - Base.metadata.create_all(engine)

"""Create all tables from the models (quick start; switch to Alembic migrations later).

Run from the project root:   python -m scripts.create_tables
"""
from app.core.database import Base, engine
import app.models  # noqa: F401  (registers every model on Base.metadata)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    main()
