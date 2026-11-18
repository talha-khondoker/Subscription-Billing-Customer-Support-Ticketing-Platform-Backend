# ----------------------------------------------------------------------
# app/schemas/common.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - Page[T]: items, total, page, page_size
#   - Message: simple {message} response

"""Shared response shapes. Owner: Member 1 (if they already pushed this file, keep theirs
and only make sure Page has: items, total, page, page_size)."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    message: str

