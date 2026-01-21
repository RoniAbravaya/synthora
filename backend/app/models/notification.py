"""
Notification Model

Stores in-app notifications for users.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum
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
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        type: Notification type
        title: Short notification title
        message: Notification message
        data: Additional data (JSON) - links, IDs, etc.
        is_read: Whether notification has been read
        
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
    
    # Notification Info
    type = Column(
        Enum(NotificationType),
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
        nullable=False,
        doc="Notification message"
    )
    data = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional data (links, IDs, etc.)"
    )
    
    # Status
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether notification has been read"
    )
    
    # Relationship
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type}, title={self.title})>"
    
    def mark_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
    
    @staticmethod
    def create_video_complete(user_id: str, video_id: str, video_title: str) -> "Notification":
        """Create a video generation complete notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.VIDEO_GENERATION_COMPLETE,
            title="Video Ready!",
            message=f"Your video '{video_title}' has been generated successfully.",
            data={"video_id": str(video_id), "action": "view_video"}
        )
    
    @staticmethod
    def create_video_failed(user_id: str, video_id: str, error_message: str) -> "Notification":
        """Create a video generation failed notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.VIDEO_GENERATION_FAILED,
            title="Video Generation Failed",
            message=f"Your video could not be generated: {error_message}",
            data={"video_id": str(video_id), "action": "retry_video"}
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
            type=NotificationType.POST_PUBLISHED,
            title=f"Posted to {platform.title()}!",
            message=f"Your video has been posted to {platform.title()} successfully.",
            data={
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
            type=NotificationType.POST_FAILED,
            title=f"Failed to Post to {platform.title()}",
            message=f"Could not post to {platform.title()}: {error_message}",
            data={
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
            type=NotificationType.VIDEO_EXPIRING_SOON,
            title="Video Expiring Soon",
            message=f"Your video '{video_title}' will expire in {days_remaining} days. Upgrade to Premium for unlimited retention.",
            data={
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
            type=NotificationType.SUBSCRIPTION_RENEWED,
            title="Subscription Renewed",
            message=f"Your {plan} subscription has been renewed. Next billing: {next_billing}",
            data={"plan": plan, "next_billing": next_billing}
        )
    
    @staticmethod
    def create_payment_failed(user_id: str) -> "Notification":
        """Create a payment failed notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SUBSCRIPTION_PAYMENT_FAILED,
            title="Payment Failed",
            message="We couldn't process your subscription payment. Please update your payment method.",
            data={"action": "update_payment"}
        )
    
    @staticmethod
    def create_subscription_cancelled(user_id: str, end_date: str) -> "Notification":
        """Create a subscription cancelled notification."""
        return Notification(
            user_id=user_id,
            type=NotificationType.SUBSCRIPTION_CANCELLED,
            title="Subscription Cancelled",
            message=f"Your subscription has been cancelled. You'll have access until {end_date}.",
            data={"end_date": end_date, "action": "resubscribe"}
        )

