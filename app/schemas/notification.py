# ----------------------------------------------------------------------
# app/schemas/notification.py
# Owner:   Member 6
# Purpose: Pydantic request/response schemas (the API contract used by the frontend).
# ----------------------------------------------------------------------


"""Notification schemas. Owner: Member 6."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import NotificationType
from app.schemas.common import Page


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime


class NotificationPage(Page[NotificationOut]):
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int
