"""
Social Account Model

Represents a connected social media account for posting videos.
OAuth tokens are stored encrypted.
"""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.post import Post


class SocialPlatform(str, enum.Enum):
    """Supported social media platforms."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class AccountStatus(str, enum.Enum):
    """Social account connection status."""
    CONNECTED = "connected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class SocialAccount(Base, UUIDMixin, TimestampMixin):
    """
    Social account model for connected social media accounts.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        platform: Social media platform (stored as string)
        platform_user_id: Platform-specific account/user ID
        username: Username on the platform
        display_name: Display name on the platform
        profile_url: URL to profile
        avatar_url: Profile picture URL
        access_token_encrypted: Encrypted OAuth access token
        refresh_token_encrypted: Encrypted OAuth refresh token
        token_expires_at: When the access token expires
        scopes: Granted OAuth scopes (array)
        is_active: Whether account is active
        status: Account connection status (stored as string)
        last_used_at: When this account was last used
        metadata: Additional metadata (JSON)
        
    Relationships:
        user: The user who connected this account
        posts: Posts made to this account
    """
    
    __tablename__ = "social_accounts"
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Platform - stored as string in DB (not PostgreSQL ENUM)
    platform = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Social media platform"
    )
    
    # Account Info - using correct column names from DB
    platform_user_id = Column(
        String(255),
        nullable=False,
        doc="Platform-specific account/user ID"
    )
    username = Column(
        String(255),
        nullable=True,
        doc="Username on the platform"
    )
    display_name = Column(
        String(255),
        nullable=True,
        doc="Display name on the platform"
    )
    profile_url = Column(
        String(500),
        nullable=True,
        doc="URL to profile"
    )
    avatar_url = Column(
        String(500),
        nullable=True,
        doc="Profile picture URL"
    )
    
    # OAuth Tokens (encrypted)
    access_token_encrypted = Column(
        Text,
        nullable=False,
        doc="Encrypted OAuth access token"
    )
    refresh_token_encrypted = Column(
        Text,
        nullable=True,
        doc="Encrypted OAuth refresh token"
    )
    token_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the access token expires"
    )
    
    # Scopes - array in DB
    scopes = Column(
        ARRAY(String(100)),
        nullable=True,
        doc="Granted OAuth scopes"
    )
    
    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether account is active"
    )
    status = Column(
        String(20),
        default="connected",
        nullable=False,
        doc="Account connection status"
    )
    
    # Last Activity
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this account was last used for posting"
    )
    
    # Additional metadata - column name is 'metadata' in DB
    # Use a different Python attribute name to avoid conflict with SQLAlchemy's metadata
    extra_metadata = Column(
        "metadata",  # Actual column name in database
        JSONB,
        nullable=True,
        doc="Additional metadata"
    )
    
    # Relationships
    user = relationship("User", back_populates="social_accounts")
    posts = relationship("Post", back_populates="social_account")
    
    def __repr__(self) -> str:
        return f"<SocialAccount(id={self.id}, platform={self.platform}, username={self.username})>"
    
    # Aliases for backwards compatibility
    @property
    def account_id(self) -> str:
        """Alias for platform_user_id."""
        return self.platform_user_id
    
    @property
    def account_name(self) -> Optional[str]:
        """Alias for username."""
        return self.username
    
    @property
    def account_avatar(self) -> Optional[str]:
        """Alias for avatar_url."""
        return self.avatar_url
    
    @property
    def account_metadata(self) -> Optional[dict]:
        """Alias for extra_metadata."""
        return self.extra_metadata
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if not self.token_expires_at:
            return False
        now = datetime.now(timezone.utc)
        # Handle both timezone-aware and naive datetimes
        if self.token_expires_at.tzinfo is None:
            return datetime.utcnow() > self.token_expires_at
        return now > self.token_expires_at
    
    @property
    def needs_refresh(self) -> bool:
        """
        Check if the token needs to be refreshed.
        Returns True if token expires within 5 minutes.
        """
        if not self.token_expires_at:
            return False
        now = datetime.now(timezone.utc)
        # Handle both timezone-aware and naive datetimes
        if self.token_expires_at.tzinfo is None:
            time_until_expiry = self.token_expires_at - datetime.utcnow()
        else:
            time_until_expiry = self.token_expires_at - now
        return time_until_expiry.total_seconds() < 300  # 5 minutes
    
    @property
    def display_name_formatted(self) -> str:
        """Get a display-friendly name for this account."""
        if self.username:
            return f"@{self.username}"
        if self.display_name:
            return self.display_name
        return f"{self.platform} account"
    
    def mark_used(self) -> None:
        """Update the last_used_at timestamp."""
        self.last_used_at = datetime.now(timezone.utc)
    
    def update_tokens(
        self,
        access_token_encrypted: str,
        refresh_token_encrypted: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Update OAuth tokens after refresh.
        
        Args:
            access_token_encrypted: New encrypted access token
            refresh_token_encrypted: New encrypted refresh token (optional)
            expires_at: New token expiry time
        """
        self.access_token_encrypted = access_token_encrypted
        if refresh_token_encrypted:
            self.refresh_token_encrypted = refresh_token_encrypted
        if expires_at:
            self.token_expires_at = expires_at
