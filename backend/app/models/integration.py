"""
Integration Model

Represents a user's API key configuration for an external AI service.
API keys are stored encrypted using Fernet encryption.

This module defines:
- IntegrationProvider: All supported providers organized by capability
- IntegrationCategory: Categories for grouping providers
- PROVIDER_CATEGORIES: Mapping of providers to their categories
- PROVIDER_RECOMMENDED_MODELS: Best model per provider
- PROVIDER_PRICING: Cost estimation data
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
    
    Organized by category:
    - Script/Text AI: For generating video scripts
    - Voice AI: For text-to-speech generation
    - Stock Media: For fetching background images/videos
    - Video Generation AI: For generating AI video clips
    - Video Assembly: For compiling final video
    """
    
    # =========================================================================
    # Script/Text AI Providers
    # =========================================================================
    OPENAI_GPT = "openai_gpt"       # GPT-4, GPT-4o, etc.
    ANTHROPIC = "anthropic"          # Claude models
    
    # =========================================================================
    # Voice AI Providers
    # =========================================================================
    OPENAI_TTS = "openai_tts"        # OpenAI Text-to-Speech
    ELEVENLABS = "elevenlabs"        # ElevenLabs
    PLAYHT = "playht"                # PlayHT
    
    # =========================================================================
    # Stock Media Providers
    # =========================================================================
    PEXELS = "pexels"                # Pexels stock media
    UNSPLASH = "unsplash"            # Unsplash stock photos
    PIXABAY = "pixabay"              # Pixabay stock media
    
    # =========================================================================
    # Video Generation AI Providers
    # =========================================================================
    OPENAI_SORA = "openai_sora"      # OpenAI Sora
    RUNWAY = "runway"                # Runway Gen-4
    VEO = "veo"                      # Google Veo 3
    LUMA = "luma"                    # Luma Dream Machine
    KLING = "kling"                  # Kling AI
    MINIMAX = "minimax"              # Minimax
    PIXVERSE = "pixverse"            # PixVerse
    HAILUO = "hailuo"                # Hailuo AI
    
    # =========================================================================
    # Video Assembly Providers
    # =========================================================================
    FFMPEG = "ffmpeg"                # FFmpeg (local, no API key)
    CREATOMATE = "creatomate"        # Creatomate
    SHOTSTACK = "shotstack"          # Shotstack


class IntegrationCategory(str, enum.Enum):
    """Integration categories for grouping providers."""
    SCRIPT = "script"
    VOICE = "voice"
    MEDIA = "media"
    VIDEO_AI = "video_ai"
    ASSEMBLY = "assembly"


# =============================================================================
# Provider to Category Mapping
# =============================================================================
PROVIDER_CATEGORIES: Dict[IntegrationProvider, IntegrationCategory] = {
    # Script providers
    IntegrationProvider.OPENAI_GPT: IntegrationCategory.SCRIPT,
    IntegrationProvider.ANTHROPIC: IntegrationCategory.SCRIPT,
    
    # Voice providers
    IntegrationProvider.OPENAI_TTS: IntegrationCategory.VOICE,
    IntegrationProvider.ELEVENLABS: IntegrationCategory.VOICE,
    IntegrationProvider.PLAYHT: IntegrationCategory.VOICE,
    
    # Media providers
    IntegrationProvider.PEXELS: IntegrationCategory.MEDIA,
    IntegrationProvider.UNSPLASH: IntegrationCategory.MEDIA,
    IntegrationProvider.PIXABAY: IntegrationCategory.MEDIA,
    
    # Video AI providers
    IntegrationProvider.OPENAI_SORA: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.RUNWAY: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.VEO: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.LUMA: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.KLING: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.MINIMAX: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.PIXVERSE: IntegrationCategory.VIDEO_AI,
    IntegrationProvider.HAILUO: IntegrationCategory.VIDEO_AI,
    
    # Assembly providers
    IntegrationProvider.FFMPEG: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.CREATOMATE: IntegrationCategory.ASSEMBLY,
    IntegrationProvider.SHOTSTACK: IntegrationCategory.ASSEMBLY,
}


# =============================================================================
# Recommended Models per Provider
# =============================================================================
PROVIDER_RECOMMENDED_MODELS: Dict[IntegrationProvider, str] = {
    # Script providers
    IntegrationProvider.OPENAI_GPT: "gpt-4o",
    IntegrationProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    
    # Voice providers
    IntegrationProvider.OPENAI_TTS: "tts-1-hd",
    IntegrationProvider.ELEVENLABS: "eleven_multilingual_v2",
    IntegrationProvider.PLAYHT: "PlayHT2.0-turbo",
    
    # Media providers (no models, just API)
    IntegrationProvider.PEXELS: "api",
    IntegrationProvider.UNSPLASH: "api",
    IntegrationProvider.PIXABAY: "api",
    
    # Video AI providers
    IntegrationProvider.OPENAI_SORA: "sora-1.0",
    IntegrationProvider.RUNWAY: "gen-4",
    IntegrationProvider.VEO: "veo-3",
    IntegrationProvider.LUMA: "dream-machine-1.5",
    IntegrationProvider.KLING: "kling-1.6",
    IntegrationProvider.MINIMAX: "video-01",
    IntegrationProvider.PIXVERSE: "v3.5",
    IntegrationProvider.HAILUO: "minimax-video",
    
    # Assembly providers
    IntegrationProvider.FFMPEG: "local",
    IntegrationProvider.CREATOMATE: "api",
    IntegrationProvider.SHOTSTACK: "api",
}


# =============================================================================
# Provider Pricing Data (for cost estimation)
# Prices are estimates based on typical usage for ~30 second video with ~5 scenes
# =============================================================================
PROVIDER_PRICING: Dict[str, Dict[str, Any]] = {
    # Script providers
    "openai_gpt": {
        "name": "OpenAI GPT-4o",
        "unit": "per 1K tokens",
        "input_cost": 0.0025,
        "output_cost": 0.01,
        "estimated_per_video": 0.05,
        "description": "Fast, intelligent script generation",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "unit": "per 1K tokens",
        "input_cost": 0.003,
        "output_cost": 0.015,
        "estimated_per_video": 0.06,
        "description": "High-quality creative writing",
    },
    
    # Voice providers
    "openai_tts": {
        "name": "OpenAI TTS",
        "unit": "per 1K characters",
        "cost": 0.015,
        "estimated_per_video": 0.08,
        "description": "Natural-sounding voices",
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "unit": "per 1K characters",
        "cost": 0.30,
        "estimated_per_video": 0.15,
        "description": "Premium voice cloning and generation",
    },
    "playht": {
        "name": "PlayHT",
        "unit": "per 1K characters",
        "cost": 0.10,
        "estimated_per_video": 0.05,
        "description": "Affordable high-quality voices",
    },
    
    # Media providers (typically free with API key)
    "pexels": {
        "name": "Pexels",
        "unit": "free",
        "estimated_per_video": 0.00,
        "description": "Free stock photos and videos",
    },
    "unsplash": {
        "name": "Unsplash",
        "unit": "free",
        "estimated_per_video": 0.00,
        "description": "Free high-resolution photos",
    },
    "pixabay": {
        "name": "Pixabay",
        "unit": "free",
        "estimated_per_video": 0.00,
        "description": "Free stock media library",
    },
    
    # Video AI providers
    "openai_sora": {
        "name": "OpenAI Sora",
        "unit": "per second",
        "cost": 0.02,
        "estimated_per_video": 0.40,
        "description": "High-quality AI video generation",
    },
    "runway": {
        "name": "Runway Gen-4",
        "unit": "per second",
        "cost": 0.05,
        "estimated_per_video": 1.00,
        "description": "Professional AI video creation",
    },
    "veo": {
        "name": "Google Veo 3",
        "unit": "per second",
        "cost": 0.03,
        "estimated_per_video": 0.60,
        "description": "Google's advanced video AI",
    },
    "luma": {
        "name": "Luma Dream Machine",
        "unit": "per generation",
        "cost": 0.30,
        "estimated_per_video": 0.90,
        "description": "Cinematic AI video generation",
    },
    "kling": {
        "name": "Kling AI",
        "unit": "per second",
        "cost": 0.02,
        "estimated_per_video": 0.40,
        "description": "Fast AI video generation",
    },
    "minimax": {
        "name": "Minimax",
        "unit": "per second",
        "cost": 0.015,
        "estimated_per_video": 0.30,
        "description": "Affordable AI video generation",
    },
    "pixverse": {
        "name": "PixVerse",
        "unit": "per generation",
        "cost": 0.20,
        "estimated_per_video": 0.60,
        "description": "Creative AI video styles",
    },
    "hailuo": {
        "name": "Hailuo AI",
        "unit": "per second",
        "cost": 0.01,
        "estimated_per_video": 0.20,
        "description": "Budget-friendly AI video",
    },
    
    # Assembly providers
    "ffmpeg": {
        "name": "FFmpeg (Local)",
        "unit": "free",
        "estimated_per_video": 0.00,
        "description": "Free local video processing",
    },
    "creatomate": {
        "name": "Creatomate",
        "unit": "per render",
        "cost": 0.10,
        "estimated_per_video": 0.10,
        "description": "Cloud video rendering API",
    },
    "shotstack": {
        "name": "Shotstack",
        "unit": "per render",
        "cost": 0.08,
        "estimated_per_video": 0.08,
        "description": "Scalable video automation",
    },
}


# =============================================================================
# Provider Display Information
# =============================================================================
PROVIDER_INFO: Dict[str, Dict[str, str]] = {
    "openai_gpt": {
        "display_name": "OpenAI GPT",
        "description": "Generate video scripts using GPT-4o",
        "docs_url": "https://platform.openai.com/docs",
        "api_key_prefix": "sk-",
    },
    "anthropic": {
        "display_name": "Anthropic Claude",
        "description": "Generate video scripts using Claude",
        "docs_url": "https://docs.anthropic.com",
        "api_key_prefix": "sk-ant-",
    },
    "openai_tts": {
        "display_name": "OpenAI TTS",
        "description": "Text-to-speech using OpenAI",
        "docs_url": "https://platform.openai.com/docs/guides/text-to-speech",
        "api_key_prefix": "sk-",
    },
    "elevenlabs": {
        "display_name": "ElevenLabs",
        "description": "Premium AI voice generation",
        "docs_url": "https://elevenlabs.io/docs",
        "api_key_prefix": "",
    },
    "playht": {
        "display_name": "PlayHT",
        "description": "AI voice generation",
        "docs_url": "https://docs.play.ht",
        "api_key_prefix": "",
    },
    "pexels": {
        "display_name": "Pexels",
        "description": "Free stock photos and videos",
        "docs_url": "https://www.pexels.com/api",
        "api_key_prefix": "",
    },
    "unsplash": {
        "display_name": "Unsplash",
        "description": "Free high-resolution photos",
        "docs_url": "https://unsplash.com/developers",
        "api_key_prefix": "",
    },
    "pixabay": {
        "display_name": "Pixabay",
        "description": "Free stock media",
        "docs_url": "https://pixabay.com/api/docs",
        "api_key_prefix": "",
    },
    "openai_sora": {
        "display_name": "OpenAI Sora",
        "description": "AI video generation",
        "docs_url": "https://platform.openai.com/docs",
        "api_key_prefix": "sk-",
    },
    "runway": {
        "display_name": "Runway Gen-4",
        "description": "Professional AI video creation",
        "docs_url": "https://docs.runwayml.com",
        "api_key_prefix": "",
    },
    "veo": {
        "display_name": "Google Veo 3",
        "description": "Google's AI video generation",
        "docs_url": "https://cloud.google.com/vertex-ai",
        "api_key_prefix": "",
    },
    "luma": {
        "display_name": "Luma Dream Machine",
        "description": "Cinematic AI video generation",
        "docs_url": "https://lumalabs.ai/docs",
        "api_key_prefix": "",
    },
    "kling": {
        "display_name": "Kling AI",
        "description": "Fast AI video generation",
        "docs_url": "https://klingai.com/docs",
        "api_key_prefix": "",
    },
    "minimax": {
        "display_name": "Minimax",
        "description": "Affordable AI video generation",
        "docs_url": "https://www.minimax.chat/docs",
        "api_key_prefix": "",
    },
    "pixverse": {
        "display_name": "PixVerse",
        "description": "Creative AI video styles",
        "docs_url": "https://pixverse.ai/docs",
        "api_key_prefix": "",
    },
    "hailuo": {
        "display_name": "Hailuo AI",
        "description": "Budget-friendly AI video",
        "docs_url": "https://hailuoai.video/docs",
        "api_key_prefix": "",
    },
    "ffmpeg": {
        "display_name": "FFmpeg (Local)",
        "description": "Local video processing (no API key needed)",
        "docs_url": "https://ffmpeg.org/documentation.html",
        "api_key_prefix": "",
    },
    "creatomate": {
        "display_name": "Creatomate",
        "description": "Cloud video rendering",
        "docs_url": "https://creatomate.com/docs",
        "api_key_prefix": "",
    },
    "shotstack": {
        "display_name": "Shotstack",
        "description": "Video automation API",
        "docs_url": "https://shotstack.io/docs",
        "api_key_prefix": "",
    },
}


def get_category_for_provider(provider: str) -> Optional[IntegrationCategory]:
    """Get the category for a provider string."""
    try:
        provider_enum = IntegrationProvider(provider)
        return PROVIDER_CATEGORIES.get(provider_enum)
    except ValueError:
        return None


def get_providers_for_category(category: IntegrationCategory) -> list:
    """Get all providers for a given category."""
    return [
        provider.value 
        for provider, cat in PROVIDER_CATEGORIES.items() 
        if cat == category
    ]


class Integration(Base):
    """
    Integration model for storing user's API keys.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        provider: The integration provider (e.g., 'openai_gpt', 'elevenlabs')
        category: Integration category (script, voice, media, video_ai, assembly)
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
        doc="Integration provider (e.g., openai_gpt, elevenlabs)"
    )
    category = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Integration category (script, voice, media, video_ai, assembly)"
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
        doc="Masked API key for display (shows last 4 chars)"
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
        return self.provider != IntegrationProvider.FFMPEG.value
    
    @property
    def display_name(self) -> str:
        """Get the display name for this provider."""
        info = PROVIDER_INFO.get(self.provider, {})
        return info.get("display_name", self.provider)
    
    @property
    def estimated_cost(self) -> float:
        """Get estimated cost per video for this provider."""
        pricing = PROVIDER_PRICING.get(self.provider, {})
        return pricing.get("estimated_per_video", 0.0)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert to response format."""
        info = PROVIDER_INFO.get(self.provider, {})
        pricing = PROVIDER_PRICING.get(self.provider, {})
        
        return {
            "id": str(self.id),
            "provider": self.provider,
            "category": self.category,
            "display_name": info.get("display_name", self.provider),
            "description": info.get("description", ""),
            "api_key_masked": self.api_key_masked,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "last_validated": str(self.last_validated_at) if self.last_validated_at else None,
            "estimated_cost": pricing.get("estimated_per_video", 0.0),
            "created_at": str(self.created_at) if self.created_at else None,
        }
