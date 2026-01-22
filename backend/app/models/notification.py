"""
Notification Model

Stores in-app notifications for users.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """
    Types of notifications.
    """
    VIDEO_GENERATION_COMPLETE = "video_generation_complete"
    VIDEO_GENERATION_FAILED = "video_generation_failed"
    POST_PUBLISHED = "post_published"
    POST_FAILED = "post_failed"
    NEW_AI_SUGGESTION = "new_ai_suggestion"
    VIDEO_EXPIRING_SOON = "video_expiring_soon"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription_payment_failed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SYSTEM = "system"


class NotificationPriority(str, enum.Enum):
    """Priority levels for notifications."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Notification(Base, UUIDMixin, TimestampMixin):
    """
    Notification model for in-app notifications.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        type: Notification type
        title: Short notification title
        message: Notification message
        priority: Notification priority
        is_read: Whether notification has been read
        is_dismissed: Whether notification has been dismissed
        action_url: URL for action button
        action_label: Label for action button
        metadata: Additional data (JSON)
        
    Relationships:
        user: The user this notification is for
    """
    
    __tablename__ = "notifications"
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Notification Info - stored as strings in DB
    type = Column(
        String(30),
        nullable=False,
        index=True,
        doc="Notification type"
    )
    title = Column(
        String(255),
        nullable=False,
        doc="Short notification title"
    )
    message = Column(
        Text,
        nullable=True,
        doc="Notification message"
    )
    priority = Column(
        String(10),
        default="medium",
        nullable=False,
        doc="Notification priority"
    )
    
    # Status
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether notification has been read"
    )
    is_dismissed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether notification has been dismissed"
    )
    
    # Action
    action_url = Column(
        String(500),
        nullable=True,
        doc="URL for action button"
    )
    action_label = Column(
        String(50),
        nullable=True,
        doc="Label for action button"
    )
    
    # Additional data - use 'extra_data' in Python but maps to 'metadata' column in DB
    extra_data = Column(
        "metadata",  # Actual column name in database
        JSONB,
        nullable=True,
        doc="Additional data (links, IDs, etc.)"
    )
    
    # Relationship
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type}, title={self.title})>"
    
    # Alias for backwards compatibility
    @property
    def data(self) -> Optional[dict]:
        """Alias for extra_data."""
        return self.extra_data
    
    def mark_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
    
    def dismiss(self) -> None:
        """Dismiss notification."""
        self.is_dismissed = True
    
    @staticmethod
    def create_video_complete(user_id: str, video_id: str, video_title: str) -> "Notification":
        """Create a video generation complete notification."""
        return Notification(
            user_id=user_id,
            type="video_generation_complete",
            title="Video Ready!",
            message=f"Your video '{video_title}' has been generated successfully.",
            extra_data={"video_id": str(video_id), "action": "view_video"}
        )
    
    @staticmethod
    def create_video_failed(user_id: str, video_id: str, error_message: str) -> "Notification":
        """Create a video generation failed notification."""
        return Notification(
            user_id=user_id,
            type="video_generation_failed",
            title="Video Generation Failed",
            message=f"Your video could not be generated: {error_message}",
            priority="high",
            extra_data={"video_id": str(video_id), "action": "retry_video"}
        )
    
    @staticmethod
    def create_post_published(
        user_id: str,
        post_id: str,
        platform: str,
        post_url: str
    ) -> "Notification":
        """Create a post published notification."""
        return Notification(
            user_id=user_id,
            type="post_published",
            title=f"Posted to {platform.title()}!",
            message=f"Your video has been posted to {platform.title()} successfully.",
            action_url=post_url,
            action_label="View Post",
            extra_data={
                "post_id": str(post_id),
                "platform": platform,
                "post_url": post_url,
            }
        )
    
    @staticmethod
    def create_post_failed(
        user_id: str,
        post_id: str,
        platform: str,
        error_message: str
    ) -> "Notification":
        """Create a post failed notification."""
        return Notification(
            user_id=user_id,
            type="post_failed",
            title=f"Failed to Post to {platform.title()}",
            message=f"Could not post to {platform.title()}: {error_message}",
            priority="high",
            extra_data={
                "post_id": str(post_id),
                "platform": platform,
            }
        )
    
    @staticmethod
    def create_video_expiring(
        user_id: str,
        video_id: str,
        video_title: str,
        days_remaining: int
    ) -> "Notification":
        """Create a video expiring soon notification."""
        return Notification(
            user_id=user_id,
            type="video_expiring_soon",
            title="Video Expiring Soon",
            message=f"Your video '{video_title}' will expire in {days_remaining} days. Upgrade to Premium for unlimited retention.",
            action_label="Upgrade",
            extra_data={
                "video_id": str(video_id),
                "days_remaining": days_remaining,
            }
        )
    
    @staticmethod
    def create_system(user_id: str, title: str, message: str) -> "Notification":
        """Create a system notification."""
        return Notification(
            user_id=user_id,
            type="system",
            title=title,
            message=message,
        )
