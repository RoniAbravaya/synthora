"""
App Settings Model

Stores system-wide application settings and feature flags.
"""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base, UUIDMixin


class AppSettings(Base, UUIDMixin):
    """
    App Settings model for system-wide configuration.
    
    This is a key-value store for application settings.
    
    Attributes:
        id: Unique identifier (UUID)
        key: Setting key (unique)
        value: Setting value (JSON)
        updated_at: When the setting was last updated
        
    Common Keys:
        - setup_completed: Whether initial setup is done
        - maintenance_mode: Whether app is in maintenance mode
        - feature_flags: Feature flag settings
        - default_limits: Default user limits
    """
    
    __tablename__ = "app_settings"
    
    key = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Setting key"
    )
    value = Column(
        JSONB,
        nullable=False,
        doc="Setting value"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="When the setting was last updated"
    )
    
    def __repr__(self) -> str:
        return f"<AppSettings(key={self.key})>"
    
    # Common setting keys as constants
    KEY_SETUP_COMPLETED = "setup_completed"
    KEY_MAINTENANCE_MODE = "maintenance_mode"
    KEY_FEATURE_FLAGS = "feature_flags"
    KEY_DEFAULT_LIMITS = "default_limits"
    
    @classmethod
    def get_default_feature_flags(cls) -> dict:
        """Get default feature flag values."""
        return {
            "ai_suggestions": True,
            "scheduling": True,
            "analytics": True,
            "video_generation": True,
            "social_posting": True,
        }
    
    @classmethod
    def get_default_limits(cls) -> dict:
        """Get default limit values."""
        return {
            "free_videos_per_day": 1,
            "free_retention_days": 30,
            "rate_limit_per_minute": 100,
            "max_video_duration": 300,
            "max_concurrent_generations": 1,
        }

