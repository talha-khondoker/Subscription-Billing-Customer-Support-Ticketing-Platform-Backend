# ----------------------------------------------------------------------
# app/routers/notifications.py
# Owner:   Member 6
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - GET  /notifications [all]  with unread count
#   - POST /notifications/{id}/read [all]
#   - POST /notifications/read-all [all]

"""Notification endpoints. Owner: Member 6. Paths are full paths; main.py adds /api/v1."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.notification import NotificationOut, NotificationPage, UnreadCountOut
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationPage)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return notification_service.list_for_user(db, user, page, page_size, unread_only)


@router.get("/notifications/unread-count", response_model=UnreadCountOut)
def get_unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"unread_count": notification_service.unread_count(db, user)}


@router.post("/notifications/read-all", response_model=Message)
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    changed = notification_service.mark_all_read(db, user)
    return {"message": f"{changed} notification(s) marked as read"}


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_one(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return notification_service.mark_read(db, user, notification_id)

