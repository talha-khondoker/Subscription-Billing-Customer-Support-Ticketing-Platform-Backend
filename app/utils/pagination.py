# ----------------------------------------------------------------------
# app/utils/pagination.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Pagination helper.
# ----------------------------------------------------------------------
# TODO:
#   - paginate(query, page, page_size) -> Page
#

from app.schemas.common import Page


def paginate(query, page=1, page_size=10):
    page = max(1, int(page))
    page_size = min(100, max(1, int(page_size)))
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)
