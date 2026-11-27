# NOTE: received without a path header; saved as scripts/make_token.py (its docstring says
#       "python -m scripts.make_token <email>").
"""DEV ONLY: print a JWT for a seeded user so you can test protected routes in Swagger
before the /auth/login endpoint exists.

    python -m scripts.make_token agent1@acme.test

Then in http://localhost:8000/docs click "Authorize" and paste the token (no "Bearer ").
"""
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models import User


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.make_token <email>")
        raise SystemExit(1)
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == sys.argv[1]))
        if user is None:
            print("No user with that email. Did you run: python -m scripts.seed ?")
            raise SystemExit(1)
        print(create_access_token(user.id, user.role, user.organization_id))
    finally:
        db.close()


if __name__ == "__main__":
    main()
