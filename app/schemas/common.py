# ----------------------------------------------------------------------
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    message: str
# app/schemas/common.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------
# TODO:
#   - Page[T]: items, total, page, page_size
#   - Message: simple {message} response
