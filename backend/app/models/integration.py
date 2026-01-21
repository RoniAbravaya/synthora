"""
Integration Model

Represents a user's API key configuration for an external AI service.
API keys are stored encrypted using Fernet encryption.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class IntegrationProvider(str, enum.Enum):
    """
    Supported integration providers.
    
    Categories:
    - Script/Text AI: openai
    - Voice AI: elevenlabs
    - Stock Media: pexels, unsplash
    - Video Generation AI: runway, sora, veo, luma, imagineart, pixverse, seedance, wan, hailuo, ltx
    - Video Assembly: ffmpeg, creatomate, shotstack, remotion, editframe
    """
    # Script/Text AI
    OPENAI = "openai"
    
    # Voice AI
    ELEVENLABS = "elevenlabs"
    
    # Stock Media
    PEXELS = "pexels"
    UNSPLASH = "unsplash"
    
    # Video Generation AI
    RUNWAY = "runway"
    SORA = "sora"
    VEO = "veo"
    LUMA = "luma"
    IMAGINEART = "imagineart"
    PIXVERSE = "pixverse"
    SEEDANCE = "seedance"
    WAN = "wan"
    HAILUO = "hailuo"
    LTX = "ltx"
    
    # Video Assembly
    FFMPEG = "ffmpeg"
    CREATOMATE = "creatomate"
    SHOTSTACK = "shotstack"
    REMOTION = "remotion"
    EDITFRAME = "editframe"


class IntegrationCategory(str, enum.Enum):
    """Integration categories for grouping."""
    SCRIPT = "script"
    VOICE = "voice"
    STOCK_MEDIA = "stock_media"
    VIDEO_AI = "video_ai"
    VIDEO_ASSEMBLY = "video_assembly"


# Mapping of providers to their categories
PROVIDER_CATEGORIES = {
    IntegrationProvider.OPENAI: IntegrationCategory.SCRIPT,
    IntegrationProvider.ELEVENLABS: IntegrationCategory.VOICE,
    IntegrationProvider.PEXELS: IntegrationCategory.STOCK_MEDIA,
    IntegrationProvider.UNSPLASH: IntegrationCategory.STOCK_MEDIA,
    IntegrationProvider.RUNWAY: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.SORA: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.VEO: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.LUMA: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.IMAGINEART: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.PIXVERSE: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.SEEDANCE: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.WAN: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.HAILUO: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.LTX: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.FFMPEG: IntegrationCategory.VIDEO_ASSEMBLY,
    IntegrationProvider.CREATOMATE: IntegrationCategory.VIDEO_ASSEMBLY,
    IntegrationProvider.SHOTSTACK: IntegrationCategory.VIDEO_ASSEMBLY,
    IntegrationProvider.REMOTION: IntegrationCategory.VIDEO_ASSEMBLY,
    IntegrationProvider.EDITFRAME: IntegrationCategory.VIDEO_ASSEMBLY,
}


class Integration(Base, UUIDMixin, TimestampMixin):
    """
    Integration model for storing user's API keys.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        provider: The integration provider
        api_key_encrypted: Encrypted API key (Fernet)
        oauth_data_encrypted: Encrypted OAuth data (for OAuth integrations)
        is_active: Whether the integration is active
        is_validated: Whether the API key has been validated
        validated_at: When the API key was last validated
        last_used_at: When the integration was last used
        error_message: Last error message if validation failed
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    
    Relationships:
        user: The user who owns this integration
    """
    
    __tablename__ = "integrations"
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Provider
    provider = Column(
        Enum(IntegrationProvider),
        nullable=False,
        index=True,
        doc="Integration provider"
    )
    
    # Encrypted Credentials
    api_key_encrypted = Column(
        Text,
        nullable=True,
        doc="Encrypted API key"
    )
    oauth_data_encrypted = Column(
        Text,
        nullable=True,
        doc="Encrypted OAuth data (JSON)"
    )
    
    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the integration is active"
    )
    is_validated = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the API key has been validated"
    )
    validated_at = Column(
        DateTime,
        nullable=True,
        doc="When the API key was last validated"
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        doc="When the integration was last used"
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Last error message if validation failed"
    )
    
    # Relationship
    user = relationship("User", back_populates="integrations")
    
    # Unique constraint: one provider per user
    __table_args__ = (
        # Each user can only have one integration per provider
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, user_id={self.user_id}, provider={self.provider})>"
    
    @property
    def category(self) -> IntegrationCategory:
        """Get the category for this integration's provider."""
        return PROVIDER_CATEGORIES.get(self.provider, IntegrationCategory.SCRIPT)
    
    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        # FFmpeg doesn't require an API key (it's local)
        return self.provider != IntegrationProvider.FFMPEG
    
    @property
    def supports_oauth(self) -> bool:
        """Check if this provider supports OAuth authentication."""
        # Currently, most providers use API keys
        # This can be expanded when OAuth support is added
        return False
    
    def mark_used(self) -> None:
        """Update the last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
    
    def mark_validated(self, success: bool, error_message: Optional[str] = None) -> None:
        """
        Update validation status.
        
        Args:
            success: Whether validation was successful
            error_message: Error message if validation failed
        """
        self.is_validated = success
        self.validated_at = datetime.utcnow()
        self.error_message = error_message if not success else None

