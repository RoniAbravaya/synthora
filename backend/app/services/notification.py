"""
Notification Service

Business logic for creating, managing, and delivering in-app notifications.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

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
        notification_type: Optional[NotificationType] = None,
        include_read: bool = True,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User UUID
            notification_type: Optional filter by type
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
            query = query.filter(Notification.notification_type == notification_type)
        
        if not include_dismissed:
            query = query.filter(Notification.is_dismissed == False)
        
        if not include_read:
            query = query.filter(Notification.is_read == False)
        
        # Order by priority (high first) then by creation date (newest first)
        query = query.order_by(
            Notification.priority.desc(),
            Notification.created_at.desc(),
        )
        
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
        from sqlalchemy import func
        
        results = self.db.query(
            Notification.notification_type,
            func.count(Notification.id),
        ).filter(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_dismissed == False,
            )
        ).group_by(Notification.notification_type).all()
        
        return {
            ntype.value if ntype else "unknown": count
            for ntype, count in results
        }
    
    # =========================================================================
    # Create Methods
    # =========================================================================
    
    def create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        related_video_id: Optional[UUID] = None,
        related_post_id: Optional[UUID] = None,
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            user_id: User UUID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Notification priority
            action_url: Optional URL for action button
            action_text: Optional text for action button
            metadata: Additional metadata
            related_video_id: Related video if applicable
            related_post_id: Related post if applicable
            
        Returns:
            Created Notification instance
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata or {},
            related_video_id=related_video_id,
            related_post_id=related_post_id,
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        logger.info(f"Created {notification_type.value} notification for user {user_id}")
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
            notification_type=NotificationType.VIDEO_COMPLETE,
            title="Video Ready! 🎬",
            message=f"Your video '{video_title}' has been generated and is ready to view.",
            priority=NotificationPriority.HIGH,
            action_url=f"/videos/{video_id}",
            action_text="View Video",
            related_video_id=video_id,
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
            notification_type=NotificationType.VIDEO_FAILED,
            title="Video Generation Failed ❌",
            message=f"We couldn't generate '{video_title}'. {error_message}",
            priority=NotificationPriority.HIGH,
            action_url=f"/videos/{video_id}",
            action_text="View Details",
            related_video_id=video_id,
            metadata={"error": error_message},
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
            notification_type=NotificationType.POST_PUBLISHED,
            title="Post Published! 📤",
            message=f"Your video has been posted to {platform_text}.",
            priority=NotificationPriority.MEDIUM,
            action_url=f"/posts/{post_id}",
            action_text="View Post",
            related_post_id=post_id,
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
            notification_type=NotificationType.POST_FAILED,
            title=f"Post to {platform} Failed ❌",
            message=f"We couldn't post to {platform}. {error_message}",
            priority=NotificationPriority.HIGH,
            action_url=f"/posts/{post_id}",
            action_text="View Details",
            related_post_id=post_id,
            metadata={"platform": platform, "error": error_message},
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
            notification_type=NotificationType.SCHEDULED_POST,
            title="Scheduled Post Reminder ⏰",
            message=f"Your post is scheduled for {time_str}.",
            priority=NotificationPriority.LOW,
            action_url=f"/posts/{post_id}",
            action_text="View Post",
            related_post_id=post_id,
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
            notification_type=NotificationType.PAYMENT_SUCCESS,
            title="Payment Successful ✅",
            message=f"Your payment of ${amount:.2f} {currency} was successful. Thank you!",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings/subscription",
            action_text="View Subscription",
        )
    
    def notify_payment_failed(
        self,
        user_id: UUID,
        error_message: str,
    ) -> Notification:
        """Notify user of failed payment."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_FAILED,
            title="Payment Failed ⚠️",
            message=f"Your payment couldn't be processed. {error_message}",
            priority=NotificationPriority.HIGH,
            action_url="/settings/subscription",
            action_text="Update Payment",
        )
    
    def notify_subscription_expiring(
        self,
        user_id: UUID,
        days_remaining: int,
    ) -> Notification:
        """Notify user that subscription is expiring soon."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
            title="Subscription Expiring Soon ⏳",
            message=f"Your premium subscription expires in {days_remaining} days. Renew to keep your benefits.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings/subscription",
            action_text="Renew Now",
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
            notification_type=NotificationType.SUBSCRIPTION_CANCELLED,
            title="Subscription Cancelled",
            message=f"Your premium subscription has been cancelled. You'll have access until {date_str}.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings/subscription",
            action_text="Reactivate",
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
            notification_type=NotificationType.INTEGRATION_ERROR,
            title=f"{integration_name} Connection Issue ⚠️",
            message=f"There's an issue with your {integration_name} integration. {error_message}",
            priority=NotificationPriority.HIGH,
            action_url="/settings/integrations",
            action_text="Fix Integration",
            metadata={"integration": integration_name, "error": error_message},
        )
    
    def notify_social_account_disconnected(
        self,
        user_id: UUID,
        platform: str,
    ) -> Notification:
        """Notify user that social account was disconnected."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SOCIAL_DISCONNECT,
            title=f"{platform} Account Disconnected",
            message=f"Your {platform} account has been disconnected. Reconnect to continue posting.",
            priority=NotificationPriority.HIGH,
            action_url="/settings/social-accounts",
            action_text="Reconnect",
            metadata={"platform": platform},
        )
    
    def notify_welcome(self, user_id: UUID, user_name: str) -> Notification:
        """Send welcome notification to new user."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM,
            title=f"Welcome to Synthora, {user_name}! 🎉",
            message="Get started by connecting your integrations and creating your first video.",
            priority=NotificationPriority.MEDIUM,
            action_url="/onboarding",
            action_text="Get Started",
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
            notification_type=NotificationType.SYSTEM,
            title=title,
            message=message,
            priority=NotificationPriority.LOW,
            action_url=action_url,
            action_text="Learn More" if action_url else None,
        )
    
    # =========================================================================
    # Update Methods
    # =========================================================================
    
    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Mark a notification as read."""
        notification = self.get_notification_by_id(notification_id, user_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
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
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow(),
        })
        self.db.commit()
        return count
    
    def dismiss_notification(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Dismiss a notification."""
        notification = self.get_notification_by_id(notification_id, user_id)
        if notification:
            notification.is_dismissed = True
            notification.dismissed_at = datetime.utcnow()
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
        ).update({
            "is_dismissed": True,
            "dismissed_at": datetime.utcnow(),
        })
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

