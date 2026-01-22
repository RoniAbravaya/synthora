"""
Integration Model

Represents a user's API key configuration for an external AI service.
API keys are stored encrypted using Fernet encryption.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

import uuid as uuid_lib
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

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
    ANTHROPIC = "anthropic"
    
    # Voice AI
    ELEVENLABS = "elevenlabs"
    PLAYHT = "playht"
    
    # Stock Media
    PEXELS = "pexels"
    UNSPLASH = "unsplash"
    PIXABAY = "pixabay"
    
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
    HEYGEN = "heygen"
    
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
    MEDIA = "media"
    VIDEO_AI = "video_ai"
    ASSEMBLY = "assembly"


# Mapping of providers to their categories
PROVIDER_CATEGORIES = {
    IntegrationProvider.OPENAI: IntegrationCategory.SCRIPT,
    IntegrationProvider.ANTHROPIC: IntegrationCategory.SCRIPT,
    IntegrationProvider.ELEVENLABS: IntegrationCategory.VOICE,
    IntegrationProvider.PLAYHT: IntegrationCategory.VOICE,
    IntegrationProvider.PEXELS: IntegrationCategory.MEDIA,
    IntegrationProvider.UNSPLASH: IntegrationCategory.MEDIA,
    IntegrationProvider.PIXABAY: IntegrationCategory.MEDIA,
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
    IntegrationProvider.HEYGEN: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.FFMPEG: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.CREATOMATE: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.SHOTSTACK: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.REMOTION: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.EDITFRAME: IntegrationCategory.ASSEMBLY,
}


class Integration(Base):
    """
    Integration model for storing user's API keys.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        provider: The integration provider
        category: Integration category
        api_key_encrypted: Encrypted API key
        api_key_masked: Masked API key for display
        is_active: Whether the integration is active
        is_valid: Whether the API key has been validated
        last_validated_at: When the API key was last validated
        validation_error: Error message if validation failed
        config: Additional configuration (JSONB)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    
    Relationships:
        user: The user who owns this integration
    """
    
    __tablename__ = "integrations"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Provider info
    provider = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Integration provider"
    )
    category = Column(
        String(20),
        nullable=False,
        doc="Integration category"
    )
    
    # Encrypted Credentials
    api_key_encrypted = Column(
        Text,
        nullable=False,
        doc="Encrypted API key"
    )
    api_key_masked = Column(
        String(50),
        nullable=False,
        doc="Masked API key for display"
    )
    
    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the integration is active"
    )
    is_valid = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the API key has been validated"
    )
    last_validated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the API key was last validated"
    )
    validation_error = Column(
        Text,
        nullable=True,
        doc="Error message if validation failed"
    )
    
    # Additional config
    config = Column(
        JSONB,
        nullable=True,
        doc="Additional configuration"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last update timestamp"
    )
    
    # Relationship
    user = relationship("User", back_populates="integrations")
    
    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, user_id={self.user_id}, provider={self.provider})>"
    
    @property
    def is_validated(self) -> bool:
        """Alias for is_valid for backwards compatibility."""
        return self.is_valid
    
    @property
    def validated_at(self) -> Optional[datetime]:
        """Alias for last_validated_at for backwards compatibility."""
        return self.last_validated_at
    
    @property
    def error_message(self) -> Optional[str]:
        """Alias for validation_error for backwards compatibility."""
        return self.validation_error
    
    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        return self.provider != "ffmpeg"
    
    def to_response(self) -> Dict[str, Any]:
        """Convert to response format."""
        return {
            "id": str(self.id),
            "provider": self.provider,
            "category": self.category,
            "api_key_masked": self.api_key_masked,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "last_validated": str(self.last_validated_at) if self.last_validated_at else None,
            "created_at": str(self.created_at) if self.created_at else None,
        }
