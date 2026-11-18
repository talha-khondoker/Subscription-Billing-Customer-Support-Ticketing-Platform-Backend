"""Pagination helpers. Owner: Member 1.

Two styles live here because the team writes queries two ways:

* paginate(query, page, page_size)          - legacy Session.query(...) style, returns a Page
* paginate_stmt(db, stmt, page, page_size)  - SQLAlchemy 2.0 select(...) style, returns a dict
                                              {"items", "total", "page", "page_size"}
                                              (same shape as Page; FastAPI validates it)
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schemas.common import Page

MAX_PAGE_SIZE = 100


def paginate(query, page=1, page_size=10):
    page = max(1, int(page))
    page_size = min(MAX_PAGE_SIZE, max(1, int(page_size)))
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


def paginate_stmt(db: Session, stmt, page: int = 1, page_size: int = 20) -> dict:
    """Run a select(...) statement (one entity) with LIMIT/OFFSET."""
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), MAX_PAGE_SIZE)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    return {"items": list(items), "total": total, "page": page, "page_size": page_size}