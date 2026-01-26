"""
Notification Service

Business logic for creating, managing, and delivering in-app notifications.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class for notification management.
    
    Handles:
    - Creating notifications
    - Retrieving user notifications
    - Marking notifications as read/dismissed
    - Cleanup of old notifications
    """
    
    def __init__(self, db: Session):
        """
        Initialize the notification service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_user_notifications(
        self,
        user_id: UUID,
        notification_type: Optional[str] = None,
        include_read: bool = True,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User UUID
            notification_type: Optional filter by type (string or enum)
            include_read: Include read notifications
            include_dismissed: Include dismissed notifications
            limit: Maximum number of notifications
            offset: Offset for pagination
            
        Returns:
            List of Notification records
        """
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if notification_type:
            # Handle both string and enum input
            type_value = notification_type.value if hasattr(notification_type, 'value') else notification_type
            query = query.filter(Notification.type == type_value)
        
        if not include_dismissed:
            query = query.filter(Notification.is_dismissed == False)
        
        if not include_read:
            query = query.filter(Notification.is_read == False)
        
        # Order by creation date (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        return query.offset(offset).limit(limit).all()
    
    def get_notification_by_id(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Optional[Notification]:
        """Get a specific notification by ID."""
        return self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        ).first()
    
    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications."""
        return self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_dismissed == False,
            )
        ).count()
    
    def get_unread_count_by_type(self, user_id: UUID) -> Dict[str, int]:
        """Get count of unread notifications grouped by type."""
        results = self.db.query(
            Notification.type,
            func.count(Notification.id),
        ).filter(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_dismissed == False,
            )
        ).group_by(Notification.type).all()
        
        return {
            ntype if ntype else "unknown": count
            for ntype, count in results
        }
    
    # =========================================================================
    # Create Methods
    # =========================================================================
    
    def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "medium",
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            user_id: User UUID
            notification_type: Type of notification (string)
            title: Notification title
            message: Notification message
            priority: Notification priority (string)
            action_url: Optional URL for action button
            action_label: Optional label for action button
            metadata: Additional metadata
            
        Returns:
            Created Notification instance
        """
        # Handle enum input
        if hasattr(notification_type, 'value'):
            notification_type = notification_type.value
        if hasattr(priority, 'value'):
            priority = priority.value
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            action_label=action_label,
            extra_data=metadata or {},
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        logger.info(f"Created {notification_type} notification for user {user_id}")
        return notification
    
    # =========================================================================
    # Convenience Create Methods
    # =========================================================================
    
    def notify_video_completed(
        self,
        user_id: UUID,
        video_id: UUID,
        video_title: str,
    ) -> Notification:
        """Notify user that video generation is complete."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.VIDEO_GENERATION_COMPLETE.value,
            title="Video Ready! 🎬",
            message=f"Your video '{video_title}' has been generated and is ready to view.",
            priority=NotificationPriority.HIGH.value,
            action_url=f"/videos/{video_id}",
            action_label="View Video",
            extra_data={"video_id": str(video_id)},
        )
    
    def notify_video_failed(
        self,
        user_id: UUID,
        video_id: UUID,
        video_title: str,
        error_message: str,
    ) -> Notification:
        """Notify user that video generation failed."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.VIDEO_GENERATION_FAILED.value,
            title="Video Generation Failed ❌",
            message=f"We couldn't generate '{video_title}'. {error_message}",
            priority=NotificationPriority.HIGH.value,
            action_url=f"/videos/{video_id}",
            action_label="View Details",
            extra_data={"video_id": str(video_id), "error": error_message},
        )
    
    def notify_post_published(
        self,
        user_id: UUID,
        post_id: UUID,
        platforms: List[str],
    ) -> Notification:
        """Notify user that post was published."""
        platform_text = ", ".join(platforms)
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_PUBLISHED.value,
            title="Post Published! 📤",
            message=f"Your video has been posted to {platform_text}.",
            priority=NotificationPriority.MEDIUM.value,
            action_url=f"/posts/{post_id}",
            action_label="View Post",
            extra_data={"post_id": str(post_id), "platforms": platforms},
        )
    
    def notify_post_failed(
        self,
        user_id: UUID,
        post_id: UUID,
        platform: str,
        error_message: str,
    ) -> Notification:
        """Notify user that post failed."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_FAILED.value,
            title=f"Post to {platform} Failed ❌",
            message=f"We couldn't post to {platform}. {error_message}",
            priority=NotificationPriority.HIGH.value,
            action_url=f"/posts/{post_id}",
            action_label="View Details",
            extra_data={"post_id": str(post_id), "platform": platform, "error": error_message},
        )
    
    def notify_scheduled_post_reminder(
        self,
        user_id: UUID,
        post_id: UUID,
        scheduled_time: datetime,
    ) -> Notification:
        """Notify user about upcoming scheduled post."""
        time_str = scheduled_time.strftime("%I:%M %p on %b %d")
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SCHEDULED_POST.value,
            title="Scheduled Post Reminder ⏰",
            message=f"Your post is scheduled for {time_str}.",
            priority=NotificationPriority.LOW.value,
            action_url=f"/posts/{post_id}",
            action_label="View Post",
            extra_data={"post_id": str(post_id)},
        )
    
    def notify_payment_success(
        self,
        user_id: UUID,
        amount: float,
        currency: str = "USD",
    ) -> Notification:
        """Notify user of successful payment."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_SUCCESS.value,
            title="Payment Successful ✅",
            message=f"Your payment of ${amount:.2f} {currency} was successful. Thank you!",
            priority=NotificationPriority.MEDIUM.value,
            action_url="/settings/subscription",
            action_label="View Subscription",
        )
    
    def notify_payment_failed(
        self,
        user_id: UUID,
        error_message: str,
    ) -> Notification:
        """Notify user of failed payment."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_PAYMENT_FAILED.value,
            title="Payment Failed ⚠️",
            message=f"Your payment couldn't be processed. {error_message}",
            priority=NotificationPriority.HIGH.value,
            action_url="/settings/subscription",
            action_label="Update Payment",
        )
    
    def notify_subscription_expiring(
        self,
        user_id: UUID,
        days_remaining: int,
    ) -> Notification:
        """Notify user that subscription is expiring soon."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_EXPIRING.value,
            title="Subscription Expiring Soon ⏳",
            message=f"Your premium subscription expires in {days_remaining} days. Renew to keep your benefits.",
            priority=NotificationPriority.MEDIUM.value,
            action_url="/settings/subscription",
            action_label="Renew Now",
        )
    
    def notify_subscription_cancelled(
        self,
        user_id: UUID,
        end_date: datetime,
    ) -> Notification:
        """Notify user that subscription was cancelled."""
        date_str = end_date.strftime("%B %d, %Y")
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_CANCELLED.value,
            title="Subscription Cancelled",
            message=f"Your premium subscription has been cancelled. You'll have access until {date_str}.",
            priority=NotificationPriority.MEDIUM.value,
            action_url="/settings/subscription",
            action_label="Reactivate",
        )
    
    def notify_integration_error(
        self,
        user_id: UUID,
        integration_name: str,
        error_message: str,
    ) -> Notification:
        """Notify user of integration error."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.INTEGRATION_ERROR.value,
            title=f"{integration_name} Connection Issue ⚠️",
            message=f"There's an issue with your {integration_name} integration. {error_message}",
            priority=NotificationPriority.HIGH.value,
            action_url="/settings/integrations",
            action_label="Fix Integration",
            extra_data={"integration": integration_name, "error": error_message},
        )
    
    def notify_social_account_disconnected(
        self,
        user_id: UUID,
        platform: str,
    ) -> Notification:
        """Notify user that social account was disconnected."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SOCIAL_DISCONNECT.value,
            title=f"{platform} Account Disconnected",
            message=f"Your {platform} account has been disconnected. Reconnect to continue posting.",
            priority=NotificationPriority.HIGH.value,
            action_url="/settings/social-accounts",
            action_label="Reconnect",
            extra_data={"platform": platform},
        )
    
    def notify_welcome(self, user_id: UUID, user_name: str) -> Notification:
        """Send welcome notification to new user."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM.value,
            title=f"Welcome to Synthora, {user_name}! 🎉",
            message="Get started by connecting your integrations and creating your first video.",
            priority=NotificationPriority.MEDIUM.value,
            action_url="/onboarding",
            action_label="Get Started",
        )
    
    def notify_system_announcement(
        self,
        user_id: UUID,
        title: str,
        message: str,
        action_url: Optional[str] = None,
    ) -> Notification:
        """Send system announcement to user."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM.value,
            title=title,
            message=message,
            priority=NotificationPriority.LOW.value,
            action_url=action_url,
            action_label="Learn More" if action_url else None,
        )
    
    # =========================================================================
    # Update Methods
    # =========================================================================
    
    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Mark a notification as read."""
        notification = self.get_notification_by_id(notification_id, user_id)
        if notification:
            notification.is_read = True
            self.db.commit()
            self.db.refresh(notification)
        return notification
    
    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        count = self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        ).update({"is_read": True})
        self.db.commit()
        return count
    
    def dismiss_notification(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Dismiss a notification."""
        notification = self.get_notification_by_id(notification_id, user_id)
        if notification:
            notification.is_dismissed = True
            self.db.commit()
            self.db.refresh(notification)
        return notification
    
    def dismiss_all(self, user_id: UUID) -> int:
        """Dismiss all notifications for a user."""
        count = self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.is_dismissed == False,
            )
        ).update({"is_dismissed": True})
        self.db.commit()
        return count
    
    # =========================================================================
    # Cleanup Methods
    # =========================================================================
    
    def cleanup_old_notifications(self, days: int = 90) -> int:
        """
        Remove old read/dismissed notifications.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of notifications deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        count = self.db.query(Notification).filter(
            and_(
                Notification.created_at < cutoff,
                or_(
                    Notification.is_read == True,
                    Notification.is_dismissed == True,
                ),
            )
        ).delete()
        
        self.db.commit()
        logger.info(f"Cleaned up {count} old notifications")
        return count
    
    # =========================================================================
    # Broadcast Methods
    # =========================================================================
    
    def broadcast_to_all_users(
        self,
        title: str,
        message: str,
        action_url: Optional[str] = None,
    ) -> int:
        """
        Send notification to all active users.
        
        Args:
            title: Notification title
            message: Notification message
            action_url: Optional action URL
            
        Returns:
            Number of notifications created
        """
        users = self.db.query(User).filter(User.is_active == True).all()
        
        count = 0
        for user in users:
            self.notify_system_announcement(
                user_id=user.id,
                title=title,
                message=message,
                action_url=action_url,
            )
            count += 1
        
        logger.info(f"Broadcast notification to {count} users")
        return count


def get_notification_service(db: Session) -> NotificationService:
    """Factory function to create a NotificationService instance."""
    return NotificationService(db)
