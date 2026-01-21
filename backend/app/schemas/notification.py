"""
Notification Pydantic Schemas

Request and response schemas for notification-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.notification import NotificationType, NotificationPriority


# =============================================================================
# Response Schemas
# =============================================================================

class NotificationResponse(IDSchema, TimestampSchema):
    """Full notification response."""
    
    notification_type: str
    title: str
    message: str
    priority: str
    is_read: bool
    is_dismissed: bool
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    related_video_id: Optional[UUID] = None
    related_post_id: Optional[UUID] = None


class NotificationListItem(BaseSchema):
    """Notification list item (condensed)."""
    
    id: UUID
    notification_type: str
    title: str
    message: str
    priority: str
    is_read: bool
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    created_at: datetime


class NotificationListResponse(BaseSchema):
    """List of notifications."""
    
    notifications: List[NotificationListItem]
    total: int
    unread_count: int
    has_more: bool = False


class UnreadCountResponse(BaseSchema):
    """Unread notification count."""
    
    count: int
    by_type: Dict[str, int] = Field(default_factory=dict)


class MarkReadResponse(BaseSchema):
    """Response after marking notification(s) as read."""
    
    message: str
    count: int = Field(description="Number of notifications marked as read")


class DismissResponse(BaseSchema):
    """Response after dismissing notification(s)."""
    
    message: str
    count: int = Field(description="Number of notifications dismissed")


# =============================================================================
# Request Schemas
# =============================================================================

class MarkReadRequest(BaseSchema):
    """Request to mark specific notifications as read."""
    
    notification_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific notification IDs to mark as read. If empty, marks all as read."
    )


class DismissRequest(BaseSchema):
    """Request to dismiss specific notifications."""
    
    notification_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific notification IDs to dismiss. If empty, dismisses all."
    )


# =============================================================================
# Admin Schemas
# =============================================================================

class BroadcastRequest(BaseSchema):
    """Request to broadcast notification to all users."""
    
    title: str = Field(min_length=1, max_length=100, description="Notification title")
    message: str = Field(min_length=1, max_length=500, description="Notification message")
    action_url: Optional[str] = Field(default=None, description="Optional action URL")


class BroadcastResponse(BaseSchema):
    """Response after broadcasting notification."""
    
    message: str
    users_notified: int

