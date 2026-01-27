"""
Admin Service

Business logic for platform administration and management.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.models.user import User, UserRole
from app.models.video import Video, VideoStatus
from app.models.post import Post, PostStatus
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan
from app.models.integration import Integration
from app.models.social_account import SocialAccount
from app.models.analytics import Analytics
from app.models.template import Template
from app.models.job import Job
from app.models.app_settings import AppSettings

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service class for admin operations.
    
    Handles:
    - User management
    - Platform statistics
    - System settings
    - Content moderation
    """
    
    def __init__(self, db: Session):
        """
        Initialize the admin service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    def get_users(
        self,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get users with filtering and pagination.
        
        Args:
            search: Search by email or display name
            role: Filter by role
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            limit: Max results
            offset: Offset for pagination
            
        Returns:
            Dictionary with users and pagination info
        """
        logger.info(f"AdminService.get_users called: search={search}, role={role}, is_active={is_active}")
        
        query = self.db.query(User)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.display_name.ilike(search_term),
                )
            )
            logger.info(f"Applied search filter: {search_term}")
        
        if role:
            # Use the string value for comparison with the String column
            role_value = role.value if hasattr(role, 'value') else role
            query = query.filter(User.role == role_value)
            logger.info(f"Applied role filter: {role_value}")
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
            logger.info(f"Applied is_active filter: {is_active}")
        
        # Get total count
        total = query.count()
        logger.info(f"Total users matching filters: {total}")
        
        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        users = query.offset(offset).limit(limit).all()
        logger.info(f"Users fetched after pagination: {len(users)}")
        
        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(users) < total,
        }
    
    def get_user_details(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            User details with stats
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        # Get counts
        video_count = self.db.query(Video).filter(Video.user_id == user_id).count()
        post_count = self.db.query(Post).filter(Post.user_id == user_id).count()
        integration_count = self.db.query(Integration).filter(
            Integration.user_id == user_id
        ).count()
        social_account_count = self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id
        ).count()
        
        return {
            "user": user,
            "subscription": subscription,
            "stats": {
                "videos": video_count,
                "posts": post_count,
                "integrations": integration_count,
                "social_accounts": social_account_count,
            },
        }
    
    def update_user_role(self, user_id: UUID, new_role: UserRole) -> Optional[User]:
        """
        Update a user's role.
        
        Args:
            user_id: User UUID
            new_role: New role
            
        Returns:
            Updated user or None
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        old_role = user.role
        user.role = new_role
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Changed user {user_id} role from {old_role} to {new_role}")
        return user
    
    def update_user_status(self, user_id: UUID, is_active: bool) -> Optional[User]:
        """
        Enable or disable a user account.
        
        Args:
            user_id: User UUID
            is_active: New active status
            
        Returns:
            Updated user or None
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        
        action = "enabled" if is_active else "disabled"
        logger.info(f"User {user_id} account {action}")
        return user
    
    def delete_user(self, user_id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete a user account.
        
        Args:
            user_id: User UUID
            hard_delete: If True, permanently delete. Otherwise, soft delete.
            
        Returns:
            True if deleted
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return False
        
        if hard_delete:
            # Delete all related data
            self.db.query(Video).filter(Video.user_id == user_id).delete()
            self.db.query(Post).filter(Post.user_id == user_id).delete()
            self.db.query(Integration).filter(Integration.user_id == user_id).delete()
            self.db.query(SocialAccount).filter(SocialAccount.user_id == user_id).delete()
            self.db.query(Subscription).filter(Subscription.user_id == user_id).delete()
            self.db.delete(user)
            logger.info(f"Hard deleted user {user_id}")
        else:
            # Soft delete
            user.is_active = False
            user.email = f"deleted_{user_id}@deleted.local"
            logger.info(f"Soft deleted user {user_id}")
        
        self.db.commit()
        return True
    
    # =========================================================================
    # Platform Statistics
    # =========================================================================
    
    def get_platform_stats(self) -> Dict[str, Any]:
        """
        Get overall platform statistics.
        
        Returns:
            Dictionary with platform stats
        """
        # User stats
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        
        users_by_role = dict(
            self.db.query(User.role, func.count(User.id))
            .group_by(User.role).all()
        )
        
        # Get new users in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_users_30d = self.db.query(User).filter(
            User.created_at >= thirty_days_ago
        ).count()
        
        # Video stats
        total_videos = self.db.query(Video).count()
        videos_by_status = dict(
            self.db.query(Video.status, func.count(Video.id))
            .group_by(Video.status).all()
        )
        
        # Post stats
        total_posts = self.db.query(Post).count()
        posts_by_status = dict(
            self.db.query(Post.status, func.count(Post.id))
            .group_by(Post.status).all()
        )
        
        # Subscription stats
        total_subscriptions = self.db.query(Subscription).count()
        active_subscriptions = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).count()
        
        subscriptions_by_plan = dict(
            self.db.query(Subscription.plan, func.count(Subscription.id))
            .filter(Subscription.status == SubscriptionStatus.ACTIVE)
            .group_by(Subscription.plan).all()
        )
        
        # Calculate MRR
        monthly_count = subscriptions_by_plan.get(SubscriptionPlan.MONTHLY, 0)
        annual_count = subscriptions_by_plan.get(SubscriptionPlan.ANNUAL, 0)
        mrr = (monthly_count * 5.0) + (annual_count * (50.0 / 12))
        
        def _get_enum_value(val):
            """Helper to safely get enum value or return string as-is."""
            if val is None:
                return "none"
            return val if isinstance(val, str) else val.value
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "new_30d": new_users_30d,
                "by_role": {
                    _get_enum_value(role): count
                    for role, count in users_by_role.items()
                },
            },
            "videos": {
                "total": total_videos,
                "by_status": {
                    _get_enum_value(status): count
                    for status, count in videos_by_status.items()
                },
            },
            "posts": {
                "total": total_posts,
                "by_status": {
                    _get_enum_value(status): count
                    for status, count in posts_by_status.items()
                },
            },
            "subscriptions": {
                "total": total_subscriptions,
                "active": active_subscriptions,
                "by_plan": {
                    _get_enum_value(plan): count
                    for plan, count in subscriptions_by_plan.items()
                },
                "mrr": round(mrr, 2),
                "arr": round(mrr * 12, 2),
            },
        }
    
    def get_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get activity statistics over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Activity statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Daily user signups
        daily_signups = self.db.query(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        ).filter(
            User.created_at >= cutoff
        ).group_by(func.date(User.created_at)).order_by("date").all()
        
        # Daily videos created
        daily_videos = self.db.query(
            func.date(Video.created_at).label("date"),
            func.count(Video.id).label("count"),
        ).filter(
            Video.created_at >= cutoff
        ).group_by(func.date(Video.created_at)).order_by("date").all()
        
        # Daily posts
        daily_posts = self.db.query(
            func.date(Post.created_at).label("date"),
            func.count(Post.id).label("count"),
        ).filter(
            Post.created_at >= cutoff
        ).group_by(func.date(Post.created_at)).order_by("date").all()
        
        return {
            "period_days": days,
            "daily_signups": [
                {"date": str(d.date), "count": d.count}
                for d in daily_signups
            ],
            "daily_videos": [
                {"date": str(d.date), "count": d.count}
                for d in daily_videos
            ],
            "daily_posts": [
                {"date": str(d.date), "count": d.count}
                for d in daily_posts
            ],
        }
    
    def get_top_users(self, metric: str = "videos", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by a metric.
        
        Args:
            metric: Metric to sort by (videos, posts, engagement)
            limit: Number of users
            
        Returns:
            List of top users
        """
        if metric == "videos":
            results = self.db.query(
                User,
                func.count(Video.id).label("count"),
            ).outerjoin(Video).group_by(User.id).order_by(
                desc("count")
            ).limit(limit).all()
        elif metric == "posts":
            results = self.db.query(
                User,
                func.count(Post.id).label("count"),
            ).outerjoin(Post).group_by(User.id).order_by(
                desc("count")
            ).limit(limit).all()
        else:
            # Default to videos
            results = self.db.query(
                User,
                func.count(Video.id).label("count"),
            ).outerjoin(Video).group_by(User.id).order_by(
                desc("count")
            ).limit(limit).all()
        
        return [
            {
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role if isinstance(user.role, str) else user.role.value,
                "count": count,
            }
            for user, count in results
        ]
    
    # =========================================================================
    # System Settings
    # =========================================================================
    
    def get_app_settings(self) -> Dict[str, Any]:
        """
        Get all application settings.
        
        Returns:
            Dictionary of settings
        """
        settings = self.db.query(AppSettings).all()
        return {s.key: s.value for s in settings}
    
    def get_setting(self, key: str) -> Optional[Any]:
        """Get a specific setting."""
        setting = self.db.query(AppSettings).filter(
            AppSettings.key == key
        ).first()
        return setting.value if setting else None
    
    def set_setting(self, key: str, value: Any, description: Optional[str] = None) -> AppSettings:
        """
        Set an application setting.
        
        Args:
            key: Setting key
            value: Setting value
            description: Optional description (not stored, kept for API compatibility)
            
        Returns:
            Updated or created setting
        """
        setting = self.db.query(AppSettings).filter(
            AppSettings.key == key
        ).first()
        
        if setting:
            setting.value = value
        else:
            setting = AppSettings(
                key=key,
                value=value,
            )
            self.db.add(setting)
        
        self.db.commit()
        self.db.refresh(setting)
        
        logger.info(f"Updated setting: {key}")
        return setting
    
    def delete_setting(self, key: str) -> bool:
        """Delete an application setting."""
        result = self.db.query(AppSettings).filter(
            AppSettings.key == key
        ).delete()
        self.db.commit()
        return result > 0
    
    # =========================================================================
    # Content Management
    # =========================================================================
    
    def get_recent_videos(self, limit: int = 20) -> List[Video]:
        """Get recently created videos."""
        return self.db.query(Video).order_by(
            desc(Video.created_at)
        ).limit(limit).all()
    
    def get_recent_posts(self, limit: int = 20) -> List[Post]:
        """Get recently created posts."""
        return self.db.query(Post).order_by(
            desc(Post.created_at)
        ).limit(limit).all()
    
    def get_failed_jobs(self, limit: int = 50) -> List[Job]:
        """Get recently failed jobs."""
        return self.db.query(Job).filter(
            Job.status == "failed"
        ).order_by(desc(Job.created_at)).limit(limit).all()
    
    # =========================================================================
    # Template Management
    # =========================================================================
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get template usage statistics."""
        total_templates = self.db.query(Template).count()
        system_templates = self.db.query(Template).filter(
            Template.is_system == True
        ).count()
        
        # Most used templates
        most_used = self.db.query(
            Template,
            func.count(Video.id).label("usage_count"),
        ).outerjoin(Video).group_by(Template.id).order_by(
            desc("usage_count")
        ).limit(10).all()
        
        return {
            "total": total_templates,
            "system": system_templates,
            "user_created": total_templates - system_templates,
            "most_used": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "usage_count": count,
                }
                for t, count in most_used
            ],
        }


def get_admin_service(db: Session) -> AdminService:
    """Factory function to create an AdminService instance."""
    return AdminService(db)

