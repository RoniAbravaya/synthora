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


class PlanningStatus(str, enum.Enum):
    """
    Planning workflow status for scheduled videos.
    
    - none: Regular video, not part of planning workflow
    - planned: Scheduled but not yet generated
    - generating: Generation in progress (triggered by scheduler)
    - ready: Generated and waiting for posting time
    - posting: Currently being posted to platforms
    - posted: Successfully posted to all platforms
    - failed: Generation or posting failed
    """
    NONE = "none"
    PLANNED = "planned"
    GENERATING = "generating"
    READY = "ready"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


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
        status: Current generation status (stored as string)
        progress: Overall progress percentage (0-100)
        current_step: Current step in generation pipeline (stored as string)
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
    
    # Status - stored as strings in DB (not PostgreSQL ENUM)
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
        Text,
        nullable=True,
        doc="URL to the generated video (GCS signed URL)"
    )
    thumbnail_url = Column(
        Text,
        nullable=True,
        doc="URL to video thumbnail (GCS signed URL)"
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
    
    # Planning & Scheduling (for AI suggestions feature)
    scheduled_post_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="When the video should be posted"
    )
    generation_triggered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When generation was triggered by scheduler"
    )
    posted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the video was actually posted"
    )
    
    # Series management
    series_name = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Name of the video series (if part of series)"
    )
    series_order = Column(
        Integer,
        nullable=True,
        doc="Order in the series (1, 2, 3...)"
    )
    
    # Platform targeting
    target_platforms = Column(
        ARRAY(String(50)),
        nullable=True,
        doc="Platforms to post to (youtube, tiktok, instagram, facebook)"
    )
    
    # AI suggestion data
    ai_suggestion_data = Column(
        JSONB,
        nullable=True,
        doc="Complete AI-generated suggestion data for video generation"
    )
    
    # Planning workflow status
    planning_status = Column(
        String(50),
        default=PlanningStatus.NONE.value,
        nullable=True,
        index=True,
        doc="Planning workflow status (none, planned, generating, ready, posting, posted, failed)"
    )
    
    # Subtitle file
    subtitle_file_url = Column(
        Text,
        nullable=True,
        doc="URL to generated subtitle file (SRT/ASS) in cloud storage"
    )
    
    # Generation timing for tracking and stuck detection
    generation_started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when video generation actually started processing"
    )
    last_step_updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Last time a generation step was updated (for stuck job detection)"
    )
    
    # Selected providers for this video
    selected_providers = Column(
        JSONB,
        nullable=True,
        doc="Providers selected for this video: {script, voice, media, video_ai, assembly}"
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
    
    @property
    def is_planned(self) -> bool:
        """Check if video is planned/scheduled but not yet generated."""
        return self.planning_status == PlanningStatus.PLANNED.value
    
    @property
    def is_ready_to_post(self) -> bool:
        """Check if video is generated and ready to post."""
        return self.planning_status == PlanningStatus.READY.value
    
    @property
    def is_part_of_series(self) -> bool:
        """Check if video is part of a series."""
        return self.series_name is not None
    
    @property
    def series_title(self) -> Optional[str]:
        """Get the full series title with part number."""
        if not self.series_name or not self.series_order:
            return self.title
        return f"{self.series_name} - Part {self.series_order}"
    
    # Aliases for backwards compatibility
    @property
    def generation_state(self) -> Optional[Dict]:
        """Alias for generation_config."""
        return self.generation_config
    
    @property
    def error_log(self) -> Optional[Dict]:
        """Get error info as dict."""
        if self.error_message:
            return {"message": self.error_message}
        return None
    
    @property
    def settings_snapshot(self) -> Optional[Dict]:
        """Alias for config."""
        return self.config
    
    def get_step_status(self, step: GenerationStep) -> Dict[str, Any]:
        """
        Get the status of a specific generation step.
        
        Args:
            step: The generation step to check
            
        Returns:
            Dict with status, progress, and any results
        """
        if not self.generation_config:
            return {"status": "pending", "progress": 0, "result": None, "error": None}
        step_data = self.generation_config.get(step.value, {})
        return {
            "status": step_data.get("status", "pending"),
            "progress": step_data.get("progress", 0),
            "result": step_data.get("result"),
            "error": step_data.get("error"),
        }
    
    def update_step(
        self,
        step: GenerationStep,
        status: str,
        progress: int = 0,
        result: Any = None,
        error: str = None
    ) -> None:
        """
        Update the status of a generation step.
        
        Args:
            step: The generation step to update
            status: New status (pending, processing, completed, failed)
            progress: Progress percentage for this step
            result: Any result data from the step
            error: Error message if failed
        """
        if not self.generation_config:
            self.generation_config = {}
        
        self.generation_config[step.value] = {
            "status": status,
            "progress": progress,
            "result": result,
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Update current step (as string)
        self.current_step = step.value
        
        # Calculate overall progress
        steps = list(GenerationStep)
        completed_steps = sum(
            1 for s in steps
            if self.generation_config.get(s.value, {}).get("status") == "completed"
        )
        self.progress = int((completed_steps / len(steps)) * 100)
    
    def get_last_successful_step(self) -> Optional[GenerationStep]:
        """
        Get the last successfully completed step.
        Useful for resuming failed generations.
        
        Returns:
            The last completed step, or None if no steps completed
        """
        if not self.generation_config:
            return None
        steps = list(GenerationStep)
        last_completed = None
        
        for step in steps:
            step_data = self.generation_config.get(step.value, {})
            if step_data.get("status") == "completed":
                last_completed = step
            else:
                break
        
        return last_completed
    
    def set_error(self, error_message: str, error_details: Dict = None) -> None:
        """
        Set error information when generation fails.
        
        Args:
            error_message: Human-readable error message
            error_details: Additional error details (stack trace, API response, etc.)
        """
        self.status = "failed"
        self.error_message = error_message
