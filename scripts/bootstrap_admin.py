# NOTE: received without a path header; saved as scripts/bootstrap_admin.py (its docstring says
#       "python -m scripts.bootstrap_admin").
"""Bootstrap the first platform Super Admin.

Run from the project root with: python -m scripts.bootstrap_admin
"""
from scripts.create_admin import main


if __name__ == "__main__":
    raise SystemExit(main())
