"""
User Model

Represents a user account in the Synthora platform.
Users can have different roles: admin, premium, or free.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.integration import Integration
    from app.models.template import Template
    from app.models.video import Video
    from app.models.social_account import SocialAccount
    from app.models.post import Post
    from app.models.ai_suggestion import AISuggestion
    from app.models.notification import Notification


class UserRole(str, enum.Enum):
    """
    User role enumeration.
    
    - admin: Full system access, user management, system templates
    - premium: Paid subscriber with full feature access
    - free: Free tier with limited features
    """
    ADMIN = "admin"
    PREMIUM = "premium"
    FREE = "free"


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model representing a registered user.
    
    Attributes:
        id: Unique identifier (UUID)
        email: User's email address (from Firebase)
        name: Display name
        avatar_url: Profile picture URL
        role: User role (admin, premium, free)
        firebase_uid: Firebase Authentication UID
        is_active: Whether the account is active
        last_login_at: Timestamp of last login
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    
    Relationships:
        subscription: User's subscription (one-to-one)
        integrations: User's API key configurations (one-to-many)
        templates: User's personal templates (one-to-many)
        videos: User's generated videos (one-to-many)
        social_accounts: Connected social media accounts (one-to-many)
        posts: User's posts (one-to-many)
        suggestions: AI suggestions for user (one-to-many)
        notifications: User's notifications (one-to-many)
    """
    
    __tablename__ = "users"
    
    # Basic Info
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address"
    )
    name = Column(
        String(255),
        nullable=True,
        doc="User's display name"
    )
    avatar_url = Column(
        Text,
        nullable=True,
        doc="URL to user's profile picture"
    )
    
    # Authentication
    firebase_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="Firebase Authentication UID"
    )
    
    # Role & Status
    role = Column(
        Enum(UserRole),
        default=UserRole.FREE,
        nullable=False,
        index=True,
        doc="User's role (admin, premium, free)"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the account is active"
    )
    
    # Activity Tracking
    last_login_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp of last login"
    )
    
    # Relationships
    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    integrations = relationship(
        "Integration",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    templates = relationship(
        "Template",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Template.user_id"
    )
    videos = relationship(
        "Video",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    social_accounts = relationship(
        "SocialAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    suggestions = relationship(
        "AISuggestion",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    jobs = relationship(
        "Job",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium access (admin or premium)."""
        return self.role in (UserRole.ADMIN, UserRole.PREMIUM)
    
    @property
    def can_schedule(self) -> bool:
        """Check if user can schedule posts."""
        return self.is_premium
    
    @property
    def can_access_ai_suggestions(self) -> bool:
        """Check if user can access AI suggestions."""
        return self.is_premium
    
    @property
    def daily_video_limit(self) -> Optional[int]:
        """Get user's daily video generation limit."""
        if self.is_premium:
            return None  # Unlimited
        return 1  # Free users: 1 per day
    
    @property
    def video_retention_days(self) -> Optional[int]:
        """Get user's video retention period in days."""
        if self.is_premium:
            return None  # Indefinite
        return 30  # Free users: 30 days

