# ----------------------------------------------------------------------
# scripts/reset_db.py
# Owner:   Member 1
# Purpose: Drop, create and seed the database.
# ----------------------------------------------------------------------
"""DEV ONLY: drop every table, create them again and load the demo data.

Run from the project root:   python -m scripts.reset_db
"""
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401  (registers every model on Base.metadata)
from scripts.seed import DEFAULT_PASSWORD, seed


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    print("Database reset and seeded. Password for every demo account:", DEFAULT_PASSWORD)


if __name__ == "__main__":
    main()
