"""
Social Account Model

Represents a connected social media account for posting videos.
OAuth tokens are stored encrypted.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
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
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class SocialAccount(Base, UUIDMixin, TimestampMixin):
    """
    Social account model for connected social media accounts.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        platform: Social media platform
        
        # Account Info
        account_id: Platform-specific account/user ID
        account_name: Display name or username
        account_avatar: Profile picture URL
        
        # OAuth Tokens (encrypted)
        access_token_encrypted: Encrypted OAuth access token
        refresh_token_encrypted: Encrypted OAuth refresh token
        token_expires_at: When the access token expires
        
        # Scopes
        scopes: Granted OAuth scopes
        
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
    
    # Platform
    platform = Column(
        Enum(SocialPlatform),
        nullable=False,
        index=True,
        doc="Social media platform"
    )
    
    # Account Info
    account_id = Column(
        String(255),
        nullable=False,
        doc="Platform-specific account/user ID"
    )
    account_name = Column(
        String(255),
        nullable=True,
        doc="Display name or username"
    )
    account_avatar = Column(
        Text,
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
        DateTime,
        nullable=True,
        doc="When the access token expires"
    )
    
    # Scopes
    scopes = Column(
        Text,
        nullable=True,
        doc="Granted OAuth scopes (comma-separated)"
    )
    
    # Last Activity
    last_used_at = Column(
        DateTime,
        nullable=True,
        doc="When this account was last used for posting"
    )
    
    # Relationships
    user = relationship("User", back_populates="social_accounts")
    posts = relationship("Post", back_populates="social_account")
    
    # Unique constraint: one account per platform per user
    __table_args__ = (
        # Note: In production, you might want to allow multiple accounts per platform
        # For now, we limit to one per platform as specified in requirements
    )
    
    def __repr__(self) -> str:
        return f"<SocialAccount(id={self.id}, platform={self.platform}, account_name={self.account_name})>"
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() > self.token_expires_at
    
    @property
    def needs_refresh(self) -> bool:
        """
        Check if the token needs to be refreshed.
        Returns True if token expires within 5 minutes.
        """
        if not self.token_expires_at:
            return False
        time_until_expiry = self.token_expires_at - datetime.utcnow()
        return time_until_expiry.total_seconds() < 300  # 5 minutes
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for this account."""
        if self.account_name:
            return f"@{self.account_name}"
        return f"{self.platform.value} account"
    
    def mark_used(self) -> None:
        """Update the last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
    
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

