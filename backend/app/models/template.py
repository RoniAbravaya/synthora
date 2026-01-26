"""
Template Model

Represents a video generation template with all configuration parameters.
Templates can be system-wide (created by admins, user_id=NULL) or personal (created by users).
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class TemplateCategory(str, enum.Enum):
    """Template content categories."""
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    PRODUCT = "product"
    MOTIVATIONAL = "motivational"
    NEWS = "news"
    HOWTO = "howto"
    LIFESTYLE = "lifestyle"
    GENERAL = "general"


class Template(Base):
    """
    Template model for video generation configurations.
    
    This model matches the database schema from migration 001_initial_schema.
    Templates with user_id=NULL are system templates.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user (null for system templates)
        name: Template name
        description: Template description
        category: Content category
        is_public: Whether other users can see this template
        is_premium: Whether this is a premium-only template
        is_featured: Whether this is a featured template
        thumbnail_url: URL to template thumbnail
        preview_url: URL to template preview video
        config: JSONB configuration for video generation
        tags: Searchable tags
        use_count: Number of times used
        created_at: Creation timestamp
        updated_at: Last update timestamp
        
    Relationships:
        user: The user who created this template (null for system)
        videos: Videos created using this template
    """
    
    __tablename__ = "templates"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    
    # Foreign Key (nullable for system templates)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Foreign key to user (null for system templates)"
    )
    
    # Basic Info
    name = Column(
        String(255),
        nullable=False,
        doc="Template name"
    )
    description = Column(
        Text,
        nullable=True,
        doc="Template description"
    )
    category = Column(
        String(50),
        nullable=False,
        default="general",
        index=True,
        doc="Content category"
    )
    
    # Visibility and status
    is_public = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Whether other users can see this template"
    )
    is_premium = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether this is a premium-only template"
    )
    is_featured = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether this is a featured template"
    )
    
    # Media
    thumbnail_url = Column(
        Text,
        nullable=True,
        doc="URL to template thumbnail"
    )
    preview_url = Column(
        Text,
        nullable=True,
        doc="URL to template preview video"
    )
    
    # Configuration (JSONB matching database schema)
    config = Column(
        JSONB,
        nullable=False,
        default=dict,
        doc="JSONB configuration for video generation"
    )
    
    # Tags
    tags = Column(
        ARRAY(String(50)),
        nullable=True,
        doc="Searchable tags"
    )
    
    # Usage tracking
    use_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of times this template has been used"
    )
    
    # Timestamps
    created_at = Column(
        String,
        nullable=True,
        doc="Creation timestamp"
    )
    updated_at = Column(
        String,
        nullable=True,
        doc="Last update timestamp"
    )
    
    # Relationships
    user = relationship("User", back_populates="templates", foreign_keys=[user_id])
    videos = relationship("Video", back_populates="template")
    
    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name={self.name}, is_system={self.is_system})>"
    
    @property
    def is_system(self) -> bool:
        """Check if this is a system template (no user_id)."""
        return self.user_id is None
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the config JSONB."""
        if not self.config:
            return default
        return self.config.get(key, default)
    
    def to_frontend_format(self) -> Dict[str, Any]:
        """
        Export template in format expected by frontend.
        Returns the full template data including nested config.
        """
        config = self.config or {}
        
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "is_system": self.is_system,
            "is_public": self.is_public,
            "is_premium": self.is_premium,
            "is_featured": self.is_featured,
            "tags": self.tags or [],
            "use_count": self.use_count,
            "config": {
                "video_structure": {
                    "duration_seconds": config.get("duration_max", 60),
                    "aspect_ratio": config.get("aspect_ratio", "9:16"),
                    "segments": [
                        {
                            "type": "hook",
                            "duration_seconds": 3,
                            "description": config.get("hook_style", "question")
                        },
                        {
                            "type": "body",
                            "duration_seconds": config.get("duration_max", 60) - 6,
                            "description": config.get("narrative_structure", "hook_story_payoff")
                        },
                        {
                            "type": "cta",
                            "duration_seconds": 3,
                            "description": "Call to action"
                        }
                    ]
                },
                "visual_style": {
                    "color_scheme": "modern",
                    "font_family": "Inter",
                    "transition_style": "cut",
                    "overlay_style": "minimal"
                },
                "audio": {
                    "voice_style": config.get("voice_tone", "professional"),
                    "background_music_genre": config.get("music_mood", "upbeat"),
                    "sound_effects": True
                },
                "script_prompt": {
                    "tone": config.get("voice_tone", "professional"),
                    "hook_style": config.get("hook_style", "question"),
                    "call_to_action": "Follow for more",
                    "content_structure": [
                        "hook",
                        "problem",
                        "solution",
                        "cta"
                    ]
                },
                "platform_optimization": {
                    "primary_platform": "tiktok",
                    "hashtag_strategy": "trending",
                    "caption_style": "engaging"
                }
            },
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None
        }
