"""
Notification API Endpoints

Endpoints for managing user notifications.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.notification import NotificationType
from app.services.notification import NotificationService
from app.schemas.notification import (
    NotificationResponse,
    NotificationListItem,
    NotificationListResponse,
    UnreadCountResponse,
    MarkReadRequest,
    MarkReadResponse,
    DismissRequest,
    DismissResponse,
    BroadcastRequest,
    BroadcastResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# =============================================================================
# List Endpoints
# =============================================================================

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    notification_type: Optional[str] = Query(default=None, description="Filter by type"),
    include_read: bool = Query(default=True, description="Include read notifications"),
    include_dismissed: bool = Query(default=False, description="Include dismissed notifications"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get notifications for the current user.
    
    Returns notifications ordered by priority and creation date.
    """
    service = NotificationService(db)
    
    # Pass type filter directly as string
    notifications = service.get_user_notifications(
        current_user.id,
        notification_type=notification_type,
        include_read=include_read,
        include_dismissed=include_dismissed,
        limit=limit + 1,  # Get one extra to check if there's more
        offset=offset,
    )
    
    # Check if there are more results
    has_more = len(notifications) > limit
    if has_more:
        notifications = notifications[:limit]
    
    unread_count = service.get_unread_count(current_user.id)
    
    return NotificationListResponse(
        notifications=[
            NotificationListItem(
                id=n.id,
                notification_type=n.type,
                title=n.title,
                message=n.message or "",
                priority=n.priority,
                is_read=n.is_read,
                action_url=n.action_url,
                action_text=n.action_label,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=len(notifications),
        unread_count=unread_count,
        has_more=has_more,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get count of unread notifications.
    
    Returns total count and count by type.
    """
    service = NotificationService(db)
    
    count = service.get_unread_count(current_user.id)
    by_type = service.get_unread_count_by_type(current_user.id)
    
    return UnreadCountResponse(count=count, by_type=by_type)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific notification by ID.
    """
    service = NotificationService(db)
    notification = service.get_notification_by_id(notification_id, current_user.id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.type,
        title=notification.title,
        message=notification.message or "",
        priority=notification.priority,
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        action_url=notification.action_url,
        action_text=notification.action_label,
        metadata=notification.metadata or {},
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


# =============================================================================
# Mark Read Endpoints
# =============================================================================

@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark a specific notification as read.
    """
    service = NotificationService(db)
    notification = service.mark_as_read(notification_id, current_user.id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.type,
        title=notification.title,
        message=notification.message or "",
        priority=notification.priority,
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        action_url=notification.action_url,
        action_text=notification.action_label,
        metadata=notification.metadata or {},
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.post("/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications as read.
    """
    service = NotificationService(db)
    count = service.mark_all_as_read(current_user.id)
    
    return MarkReadResponse(
        message=f"Marked {count} notifications as read",
        count=count,
    )


# =============================================================================
# Dismiss Endpoints
# =============================================================================

@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Dismiss a specific notification.
    
    Dismissed notifications won't appear in the list by default.
    """
    service = NotificationService(db)
    notification = service.dismiss_notification(notification_id, current_user.id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.type,
        title=notification.title,
        message=notification.message or "",
        priority=notification.priority,
        is_read=notification.is_read,
        is_dismissed=notification.is_dismissed,
        action_url=notification.action_url,
        action_text=notification.action_label,
        metadata=notification.metadata or {},
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.post("/dismiss-all", response_model=DismissResponse)
async def dismiss_all(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Dismiss all notifications.
    """
    service = NotificationService(db)
    count = service.dismiss_all(current_user.id)
    
    return DismissResponse(
        message=f"Dismissed {count} notifications",
        count=count,
    )


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/admin/broadcast", response_model=BroadcastResponse)
async def broadcast_notification(
    request: BroadcastRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Broadcast a notification to all users (admin only).
    """
    service = NotificationService(db)
    
    count = service.broadcast_to_all_users(
        title=request.title,
        message=request.message,
        action_url=request.action_url,
    )
    
    return BroadcastResponse(
        message=f"Notification broadcast to {count} users",
        users_notified=count,
    )
