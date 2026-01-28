"""
User Generation Settings Model

Stores user preferences for video generation:
- Default providers for each generation step
- Subtitle style preferences
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

import uuid as uuid_lib
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SubtitleStyle:
    """
    Available subtitle style presets.
    
    Each style defines font, size, color, and position settings
    that are applied during video assembly.
    """
    CLASSIC = "classic"   # White text, black outline, bottom position
    MODERN = "modern"     # White text, semi-transparent background, bottom
    BOLD = "bold"         # Yellow text, thick black outline, center
    MINIMAL = "minimal"   # White text, subtle background, bottom
    
    ALL = [CLASSIC, MODERN, BOLD, MINIMAL]
    DEFAULT = MODERN


# Subtitle style configurations for FFmpeg
SUBTITLE_STYLE_CONFIGS = {
    SubtitleStyle.CLASSIC: {
        "font_name": "Arial",
        "font_size": 24,
        "primary_color": "&HFFFFFF",  # White (ASS format: &HBBGGRR)
        "outline_color": "&H000000",  # Black
        "outline_width": 2,
        "shadow": 1,
        "alignment": 2,  # Bottom center
        "margin_v": 30,
        "background_color": None,
    },
    SubtitleStyle.MODERN: {
        "font_name": "Helvetica Neue",
        "font_size": 28,
        "primary_color": "&HFFFFFF",
        "outline_color": "&H000000",
        "outline_width": 1,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 40,
        "background_color": "&H80000000",  # Semi-transparent black
    },
    SubtitleStyle.BOLD: {
        "font_name": "Impact",
        "font_size": 32,
        "primary_color": "&H00FFFF",  # Yellow (BGR format)
        "outline_color": "&H000000",
        "outline_width": 3,
        "shadow": 2,
        "alignment": 5,  # Center
        "margin_v": 0,
        "background_color": None,
    },
    SubtitleStyle.MINIMAL: {
        "font_name": "Roboto",
        "font_size": 22,
        "primary_color": "&HFFFFFF",
        "outline_color": None,
        "outline_width": 0,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 25,
        "background_color": "&HB0000000",  # More opaque black
    },
}


class UserGenerationSettings(Base):
    """
    User generation settings for video creation preferences.
    
    Each user has one settings record that stores their default
    provider selections and subtitle preferences. These defaults
    are used when generating videos unless overridden.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user (unique - one per user)
        default_script_provider: Provider for script generation
        default_voice_provider: Provider for voice generation
        default_media_provider: Provider for stock media
        default_video_ai_provider: Provider for AI video generation
        default_assembly_provider: Provider for video assembly
        subtitle_style: Subtitle style preset (classic, modern, bold, minimal)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    
    Relationships:
        user: The user these settings belong to
    """
    
    __tablename__ = "user_generation_settings"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    
    # Foreign Key (unique - one settings record per user)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Foreign key to user"
    )
    
    # Default providers for each category
    default_script_provider = Column(
        String(50),
        nullable=True,
        doc="Default provider for script generation (e.g., openai_gpt, anthropic)"
    )
    default_voice_provider = Column(
        String(50),
        nullable=True,
        doc="Default provider for voice generation (e.g., elevenlabs, openai_tts)"
    )
    default_media_provider = Column(
        String(50),
        nullable=True,
        doc="Default provider for stock media (e.g., pexels, unsplash)"
    )
    default_video_ai_provider = Column(
        String(50),
        nullable=True,
        doc="Default provider for AI video generation (e.g., openai_sora, runway)"
    )
    default_assembly_provider = Column(
        String(50),
        nullable=True,
        doc="Default provider for video assembly (e.g., ffmpeg, creatomate)"
    )
    
    # Subtitle settings
    subtitle_style = Column(
        String(20),
        nullable=False,
        default=SubtitleStyle.DEFAULT,
        doc="Subtitle style preset: classic, modern, bold, minimal"
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
    user = relationship("User", back_populates="generation_settings")
    
    def __repr__(self) -> str:
        return f"<UserGenerationSettings(id={self.id}, user_id={self.user_id})>"
    
    @property
    def subtitle_config(self) -> Dict[str, Any]:
        """Get the subtitle style configuration for FFmpeg."""
        return SUBTITLE_STYLE_CONFIGS.get(
            self.subtitle_style, 
            SUBTITLE_STYLE_CONFIGS[SubtitleStyle.DEFAULT]
        )
    
    def get_default_provider(self, category: str) -> Optional[str]:
        """
        Get the default provider for a category.
        
        Args:
            category: One of 'script', 'voice', 'media', 'video_ai', 'assembly'
            
        Returns:
            Provider name or None if not set
        """
        category_map = {
            "script": self.default_script_provider,
            "voice": self.default_voice_provider,
            "media": self.default_media_provider,
            "video_ai": self.default_video_ai_provider,
            "assembly": self.default_assembly_provider,
        }
        return category_map.get(category)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert to response format."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "default_script_provider": self.default_script_provider,
            "default_voice_provider": self.default_voice_provider,
            "default_media_provider": self.default_media_provider,
            "default_video_ai_provider": self.default_video_ai_provider,
            "default_assembly_provider": self.default_assembly_provider,
            "subtitle_style": self.subtitle_style,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
