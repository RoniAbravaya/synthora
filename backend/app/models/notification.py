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
    
    - video_generation_complete: Video finished generating
    - video_generation_failed: Video generation failed
    - post_published: Post was successfully published
    - post_failed: Post publishing failed
    - new_ai_suggestion: New AI suggestion available (Premium)
    - video_expiring_soon: Video will expire soon (Free users)
    - subscription_renewed: Subscription was renewed
    - subscription_payment_failed: Subscription payment failed
    - subscription_cancelled: Subscription was cancelled
    - system: System announcement
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
    # Additional types used by notification service
    VIDEO_COMPLETE = "video_complete"
    VIDEO_FAILED = "video_failed"
    SCHEDULED_POST = "scheduled_post"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    INTEGRATION_ERROR = "integration_error"
    SOCIAL_DISCONNECT = "social_disconnect"


class NotificationPriority(str, enum.Enum):
    """
    Priority levels for notifications.
    """
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
        type: Notification type (stored as string in DB)
        title: Short notification title
        message: Notification message
        priority: Notification priority (stored as string in DB)
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
    
    # Notification Info - stored as strings in DB (not PostgreSQL ENUM)
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
    
    # Additional data - Python attr is 'extra_data', DB column is 'metadata'
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
    
    # Aliases for backwards compatibility with code using enum-style access
    @property
    def notification_type(self) -> str:
        """Alias for type field."""
        return self.type
    
    @property
    def action_text(self) -> Optional[str]:
        """Alias for action_label."""
        return self.action_label
    
    @property
    def data(self) -> Optional[dict]:
        """Alias for extra_data."""
        return self.extra_data
    
    # Note: Cannot use 'metadata' as property name - it's reserved by SQLAlchemy
    # Use 'extra_data' or 'data' instead
    
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
            type=NotificationType.VIDEO_GENERATION_COMPLETE.value,
            title="Video Ready!",
            message=f"Your video '{video_title}' has been generated successfully.",
            priority=NotificationPriority.MEDIUM.value,
            extra_data={"video_id": str(video_id), "action": "view_video"}
        )
    
    @staticmethod
    def create_video_failed(user_id: str, video_id: str, error_message: str) -> "Notification":
        """Create a video generation failed notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.VIDEO_GENERATION_FAILED.value,
            title="Video Generation Failed",
            message=f"Your video could not be generated: {error_message}",
            priority=NotificationPriority.HIGH.value,
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
            type=NotificationType.POST_PUBLISHED.value,
            title=f"Posted to {platform.title()}!",
            message=f"Your video has been posted to {platform.title()} successfully.",
            priority=NotificationPriority.MEDIUM.value,
            action_url=post_url,
            action_label="View Post",
            extra_data={
                "post_id": str(post_id),
                "platform": platform,
                "post_url": post_url,
                "action": "view_post"
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
            type=NotificationType.POST_FAILED.value,
            title=f"Failed to Post to {platform.title()}",
            message=f"Could not post to {platform.title()}: {error_message}",
            priority=NotificationPriority.HIGH.value,
            extra_data={
                "post_id": str(post_id),
                "platform": platform,
                "action": "retry_post"
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
            type=NotificationType.VIDEO_EXPIRING_SOON.value,
            title="Video Expiring Soon",
            message=f"Your video '{video_title}' will expire in {days_remaining} days. Upgrade to Premium for unlimited retention.",
            priority=NotificationPriority.MEDIUM.value,
            action_label="Upgrade",
            extra_data={
                "video_id": str(video_id),
                "days_remaining": days_remaining,
                "action": "upgrade"
            }
        )
    
    @staticmethod
    def create_subscription_renewed(user_id: str, plan: str, next_billing: str) -> "Notification":
        """Create a subscription renewed notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SUBSCRIPTION_RENEWED.value,
            title="Subscription Renewed",
            message=f"Your {plan} subscription has been renewed. Next billing: {next_billing}",
            priority=NotificationPriority.MEDIUM.value,
            extra_data={"plan": plan, "next_billing": next_billing}
        )
    
    @staticmethod
    def create_payment_failed(user_id: str) -> "Notification":
        """Create a payment failed notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SUBSCRIPTION_PAYMENT_FAILED.value,
            title="Payment Failed",
            message="We couldn't process your subscription payment. Please update your payment method.",
            priority=NotificationPriority.HIGH.value,
            extra_data={"action": "update_payment"}
        )
    
    @staticmethod
    def create_subscription_cancelled(user_id: str, end_date: str) -> "Notification":
        """Create a subscription cancelled notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SUBSCRIPTION_CANCELLED.value,
            title="Subscription Cancelled",
            message=f"Your subscription has been cancelled. You'll have access until {end_date}.",
            priority=NotificationPriority.MEDIUM.value,
            extra_data={"end_date": end_date, "action": "resubscribe"}
        )
    
    @staticmethod
    def create_system(user_id: str, title: str, message: str) -> "Notification":
        """Create a system notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SYSTEM.value,
            title=title,
            message=message,
            priority=NotificationPriority.LOW.value,
        )
