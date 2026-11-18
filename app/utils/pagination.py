# ----------------------------------------------------------------------
# app/utils/pagination.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Pagination helper.
# ----------------------------------------------------------------------
# TODO:
#   - paginate(query, page, page_size) -> Page


"""Pagination helper. Owner: Member 1 (keep theirs if already pushed and adapt calls)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

MAX_PAGE_SIZE = 100


def paginate(db: Session, stmt, page: int = 1, page_size: int = 20) -> dict:
    """Run a SELECT statement (one entity) with LIMIT/OFFSET.

    Returns a dict {"items", "total", "page", "page_size"} that matches schemas.common.Page.
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    return {"items": list(items), "total": total, "page": page, "page_size": page_size}

