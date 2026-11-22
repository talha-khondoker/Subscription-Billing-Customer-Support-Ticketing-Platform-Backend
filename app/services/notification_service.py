# ----------------------------------------------------------------------
# app/services/notification_service.py
# Owner:   Member 6
# Purpose: Business rules. Works with the DB session and models. Called by routers and jobs.
# ----------------------------------------------------------------------
# TODO:
#   - notify(db, user_id, title, message, type)
#   - list_for_user(db, user, page)
#   - mark_read(db, user, id)
#   - mark_all_read(db, user)


"""In-app notifications. Owner: Member 6.

OTHER MODULES CALL THIS:
    from app.services.notification_service import notify, notify_org_admins
    notify(db, user_id, "Payment failed", "Invoice INV-1 failed", NotificationType.PAYMENT)

notify() and notify_org_admins() only db.add + flush. They do NOT commit, so the caller's
use case stays in one transaction. The caller commits once at the end.
"""
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, Role
from app.core.exceptions import NotFound
from app.models.notification import Notification
from app.models.user import User
from app.utils.pagination import paginate


def notify(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notif_type: NotificationType = NotificationType.INFO,
    organization_id: Optional[int] = None,
) -> Optional[Notification]:
    """Create one notification for a user.

    organization_id is read from the user when not given. Users without an organization
    (the Super Admin) get no notification and None is returned.
    """
    if organization_id is None:
        target = db.get(User, user_id)
        if target is None:
            return None
        organization_id = target.organization_id
    if organization_id is None:
        return None

    notification = Notification(
        organization_id=organization_id,
        user_id=user_id,
        title=title[:150],
        message=message,
        type=notif_type,
    )
    db.add(notification)
    db.flush()
    return notification


def notify_org_admins(
    db: Session,
    organization_id: int,
    title: str,
    message: str,
    notif_type: NotificationType = NotificationType.INFO,
) -> List[Notification]:
    """Notify every active Org Admin of an organization (past_due, SLA escalation, ...)."""
    admin_ids = db.scalars(
        select(User.id).where(
            User.organization_id == organization_id,
            User.role == Role.ORG_ADMIN,
            User.is_active.is_(True),
        )
    ).all()
    created = [notify(db, uid, title, message, notif_type, organization_id=organization_id) for uid in admin_ids]
    return [n for n in created if n is not None]


def unread_count(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        )
        or 0
    )


def list_for_user(db: Session, user: User, page: int = 1, page_size: int = 20, unread_only: bool = False) -> dict:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
    result = paginate(db, stmt, page, page_size)
    result["unread_count"] = unread_count(db, user)
    return result


def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    notification = db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    )
    if notification is None:
        raise NotFound("Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> int:
    """Mark all of the user's notifications as read. Returns how many changed."""
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return result.rowcount or 0
