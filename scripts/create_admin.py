# NOTE: received without a path header; saved as scripts/create_admin.py (its docstring says
#       "python -m scripts.create_admin" and bootstrap_admin imports from it).
"""Interactively create the first platform Super Admin.

Run from the project root with: python -m scripts.create_admin
"""
from getpass import getpass
import argparse

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.enums import Role
from app.core.security import hash_password
from app.models import User  # noqa: F401
import app.models  # noqa: F401  Register all model tables before create_all.


def main() -> int:
    argparse.ArgumentParser(description="Create the first SubFlow platform Super Admin.").parse_args()
    email = input("Super Admin email: ").strip().lower()
    full_name = input("Full name: ").strip()
    password = getpass("Password (at least 8 characters): ")
    password_confirm = getpass("Confirm password: ")

    if not email or "@" not in email:
        print("Error: enter a valid email address.")
        return 1
    if not full_name:
        print("Error: full name cannot be empty.")
        return 1
    if len(password) < 8:
        print("Error: password must contain at least 8 characters.")
        return 1
    if len(password.encode("utf-8")) > 72:
        print("Error: password must be no longer than 72 UTF-8 bytes (bcrypt limit).")
        return 1
    if password != password_confirm:
        print("Error: passwords do not match.")
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == Role.SUPER_ADMIN)) is not None:
            print("Error: a Super Admin already exists. Use the existing account to manage access.")
            return 1
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            print("Error: this email is already registered.")
            return 1

        user = User(
            organization_id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=Role.SUPER_ADMIN,
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        print(f"Super Admin created: {user.email} (id={user.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
