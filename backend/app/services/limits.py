"""
Limits Service

Handles user limits and quota management.
"""

import logging
from typing import Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.services.video import VideoService

logger = logging.getLogger(__name__)


# Limit configurations
LIMITS = {
    UserRole.FREE: {
        "daily_videos": 1,
        "max_concurrent": 1,
        "video_retention_days": 30,
        "ai_suggestions": False,
    },
    UserRole.PREMIUM: {
        "daily_videos": None,  # Unlimited
        "max_concurrent": 1,
        "video_retention_days": None,  # Indefinite
        "ai_suggestions": True,
    },
    UserRole.ADMIN: {
        "daily_videos": None,
        "max_concurrent": 3,
        "video_retention_days": None,
        "ai_suggestions": True,
    },
}


class LimitsService:
    """
    Service class for managing user limits and quotas.
    
    Handles:
    - Daily video generation limits
    - Concurrent generation limits
    - Feature access based on role
    - Video retention policies
    """
    
    def __init__(self, db: Session):
        """
        Initialize the limits service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.video_service = VideoService(db)
    
    def get_user_limits(self, user: User) -> dict:
        """
        Get the limits for a user based on their role.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with limit configurations
        """
        return LIMITS.get(user.role, LIMITS[UserRole.FREE])
    
    def can_generate_video(self, user_id: UUID) -> Tuple[bool, str]:
        """
        Check if a user can generate a new video.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Tuple of (can_generate, reason)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return False, "User not found"
        
        if not user.is_active:
            return False, "Account is disabled"
        
        limits = self.get_user_limits(user)
        
        # Check daily limit
        daily_limit = limits.get("daily_videos")
        if daily_limit is not None:
            videos_today = self.video_service.count_videos_today(user_id)
            if videos_today >= daily_limit:
                return False, f"Daily limit reached ({daily_limit} video(s) per day)"
        
        return True, "OK"
    
    def can_use_ai_suggestions(self, user: User) -> bool:
        """
        Check if a user can use AI suggestions.
        
        Args:
            user: User instance
            
        Returns:
            True if user can use AI suggestions
        """
        limits = self.get_user_limits(user)
        return limits.get("ai_suggestions", False)
    
    def get_video_retention_days(self, user: User) -> int:
        """
        Get the video retention period for a user.
        
        Args:
            user: User instance
            
        Returns:
            Number of days to retain videos, or None for indefinite
        """
        limits = self.get_user_limits(user)
        return limits.get("video_retention_days")
    
    def get_remaining_daily_videos(self, user_id: UUID) -> int:
        """
        Get the remaining videos a user can generate today.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of remaining videos, or -1 for unlimited
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return 0
        
        limits = self.get_user_limits(user)
        daily_limit = limits.get("daily_videos")
        
        if daily_limit is None:
            return -1  # Unlimited
        
        videos_today = self.video_service.count_videos_today(user_id)
        return max(0, daily_limit - videos_today)
    
    def get_video_limit_info(self, user_id: UUID) -> dict:
        """
        Get video generation limit information for the frontend.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with limit, used, remaining, and resets_at
        """
        from datetime import timedelta
        
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "limit": 0,
                "used": 0,
                "remaining": 0,
                "resets_at": None,
            }
        
        limits = self.get_user_limits(user)
        daily_limit = limits.get("daily_videos")
        videos_today = self.video_service.count_videos_today(user_id)
        
        # Calculate when the limit resets (midnight UTC)
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        resets_at = tomorrow.isoformat() + "Z"
        
        if daily_limit is None:
            # Unlimited
            return {
                "limit": None,
                "used": videos_today,
                "remaining": None,
                "resets_at": resets_at,
            }
        
        return {
            "limit": daily_limit,
            "used": videos_today,
            "remaining": max(0, daily_limit - videos_today),
            "resets_at": resets_at,
        }
    
    def get_usage_stats(self, user_id: UUID) -> dict:
        """
        Get usage statistics for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with usage statistics
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {}
        
        limits = self.get_user_limits(user)
        videos_today = self.video_service.count_videos_today(user_id)
        video_stats = self.video_service.get_user_video_stats(user_id)
        
        daily_limit = limits.get("daily_videos")
        
        return {
            "role": user.role if isinstance(user.role, str) else user.role.value,
            "limits": {
                "daily_videos": daily_limit,
                "ai_suggestions": limits.get("ai_suggestions", False),
                "video_retention_days": limits.get("video_retention_days"),
            },
            "usage": {
                "videos_today": videos_today,
                "remaining_today": daily_limit - videos_today if daily_limit else None,
                "total_videos": video_stats.get("total", 0),
            },
        }


def get_limits_service(db: Session) -> LimitsService:
    """Factory function to create a LimitsService instance."""
    return LimitsService(db)

