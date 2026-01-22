"""
Video Model

Represents a generated video with its metadata, status, and generation state.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.template import Template
    from app.models.post import Post


class VideoStatus(str, enum.Enum):
    """
    Video generation status.
    
    - pending: Queued for generation
    - processing: Currently being generated
    - completed: Successfully generated
    - failed: Generation failed
    - cancelled: User cancelled generation
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationStep(str, enum.Enum):
    """Steps in the video generation pipeline."""
    SCRIPT = "script"
    VOICE = "voice"
    MEDIA = "media"
    VIDEO_AI = "video_ai"
    ASSEMBLY = "assembly"


class Video(Base, UUIDMixin, TimestampMixin):
    """
    Video model for generated videos.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        template_id: Foreign key to template (optional)
        title: Video title
        prompt: User's input prompt/topic
        status: Current generation status
        progress: Overall progress percentage (0-100)
        current_step: Current step in generation pipeline
        video_url: URL to the generated video (GCS)
        thumbnail_url: URL to video thumbnail
        duration: Video duration in seconds
        file_size: File size in bytes
        resolution: Video resolution (e.g., "1080x1920")
        config: General video configuration
        generation_config: Configuration for generation pipeline
        integrations_used: List of integrations used
        generation_time_seconds: How long generation took
        error_message: Error message if failed
        retry_count: Number of retry attempts
        expires_at: When the video expires (for free users)
        
    Relationships:
        user: The user who created this video
        template: The template used (optional)
        posts: Posts created from this video
    """
    
    __tablename__ = "videos"
    
    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to template"
    )
    
    # Basic Info
    title = Column(
        String(255),
        nullable=True,
        doc="Video title"
    )
    prompt = Column(
        Text,
        nullable=False,
        doc="User's input prompt/topic"
    )
    
    # Status - stored as strings in DB
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        doc="Current generation status"
    )
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Overall progress percentage (0-100)"
    )
    current_step = Column(
        String(50),
        nullable=True,
        doc="Current step in generation pipeline"
    )
    
    # Output
    video_url = Column(
        String(500),
        nullable=True,
        doc="URL to the generated video (GCS)"
    )
    thumbnail_url = Column(
        String(500),
        nullable=True,
        doc="URL to video thumbnail"
    )
    duration = Column(
        Float,
        nullable=True,
        doc="Video duration in seconds"
    )
    file_size = Column(
        Integer,
        nullable=True,
        doc="File size in bytes"
    )
    resolution = Column(
        String(20),
        nullable=True,
        doc="Video resolution (e.g., '1080x1920')"
    )
    
    # Configuration
    config = Column(
        JSONB,
        nullable=True,
        doc="General video configuration"
    )
    generation_config = Column(
        JSONB,
        nullable=True,
        doc="Configuration for generation pipeline"
    )
    
    # Metadata
    integrations_used = Column(
        ARRAY(String(50)),
        nullable=True,
        doc="List of integrations used"
    )
    generation_time_seconds = Column(
        Float,
        nullable=True,
        doc="How long generation took"
    )
    
    # Error handling
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if generation failed"
    )
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    
    # Retention
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="When the video expires (for free users)"
    )
    
    # Relationships
    user = relationship("User", back_populates="videos")
    template = relationship("Template", back_populates="videos")
    posts = relationship("Post", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Video(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if video generation is completed."""
        return self.status == "completed"
    
    @property
    def is_processing(self) -> bool:
        """Check if video is currently being processed."""
        return self.status == "processing"
    
    @property
    def is_failed(self) -> bool:
        """Check if video generation failed."""
        return self.status == "failed"
    
    @property
    def is_expired(self) -> bool:
        """Check if video has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def can_retry(self) -> bool:
        """Check if generation can be retried."""
        return self.status in ("failed", "cancelled")
    
    # Aliases for backwards compatibility
    @property
    def generation_state(self) -> Optional[Dict]:
        """Alias for generation_config."""
        return self.generation_config
    
    @property
    def error_log(self) -> Optional[Dict]:
        """Alias for error_message as dict."""
        if self.error_message:
            return {"message": self.error_message}
        return None
    
    @property
    def settings_snapshot(self) -> Optional[Dict]:
        """Alias for config."""
        return self.config
