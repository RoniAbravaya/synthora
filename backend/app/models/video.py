"""
Video Model

Represents a generated video with its metadata, status, and generation state.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        template_id: Foreign key to template (optional)
        
        # Basic Info
        title: Video title
        prompt: User's input prompt/topic
        description: Generated or user-provided description
        
        # Status
        status: Current generation status
        current_step: Current step in generation pipeline
        progress: Overall progress percentage (0-100)
        
        # Generation State (stores intermediate results)
        generation_state: JSON with step results and data
        error_log: JSON with error details if failed
        
        # Output
        video_url: URL to the generated video (GCS)
        thumbnail_url: URL to video thumbnail
        duration: Video duration in seconds
        file_size: File size in bytes
        resolution: Video resolution (e.g., "1080x1920")
        
        # Metadata
        integrations_used: List of integrations used
        generation_time_seconds: How long generation took
        
        # Retention
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
    description = Column(
        Text,
        nullable=True,
        doc="Video description"
    )
    
    # Status
    status = Column(
        Enum(VideoStatus),
        default=VideoStatus.PENDING,
        nullable=False,
        index=True,
        doc="Current generation status"
    )
    current_step = Column(
        Enum(GenerationStep),
        nullable=True,
        doc="Current step in generation pipeline"
    )
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Overall progress percentage (0-100)"
    )
    
    # Generation State
    generation_state = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="JSON with step results and intermediate data"
    )
    error_log = Column(
        JSONB,
        nullable=True,
        doc="JSON with error details if failed"
    )
    
    # Output
    video_url = Column(
        Text,
        nullable=True,
        doc="URL to the generated video (GCS)"
    )
    thumbnail_url = Column(
        Text,
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
    
    # Metadata
    integrations_used = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="List of integrations used"
    )
    generation_time_seconds = Column(
        Float,
        nullable=True,
        doc="How long generation took"
    )
    
    # Generation Settings (snapshot of settings used)
    settings_snapshot = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Snapshot of generation settings"
    )
    
    # Retention
    expires_at = Column(
        DateTime,
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
        return self.status == VideoStatus.COMPLETED
    
    @property
    def is_processing(self) -> bool:
        """Check if video is currently being processed."""
        return self.status == VideoStatus.PROCESSING
    
    @property
    def is_failed(self) -> bool:
        """Check if video generation failed."""
        return self.status == VideoStatus.FAILED
    
    @property
    def is_expired(self) -> bool:
        """Check if video has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def can_retry(self) -> bool:
        """Check if generation can be retried."""
        return self.status in (VideoStatus.FAILED, VideoStatus.CANCELLED)
    
    def get_step_status(self, step: GenerationStep) -> Dict[str, Any]:
        """
        Get the status of a specific generation step.
        
        Args:
            step: The generation step to check
            
        Returns:
            Dict with status, progress, and any results
        """
        step_data = self.generation_state.get(step.value, {})
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
        if not self.generation_state:
            self.generation_state = {}
        
        self.generation_state[step.value] = {
            "status": status,
            "progress": progress,
            "result": result,
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Update current step
        self.current_step = step
        
        # Calculate overall progress
        steps = list(GenerationStep)
        completed_steps = sum(
            1 for s in steps
            if self.generation_state.get(s.value, {}).get("status") == "completed"
        )
        self.progress = int((completed_steps / len(steps)) * 100)
    
    def get_last_successful_step(self) -> Optional[GenerationStep]:
        """
        Get the last successfully completed step.
        Useful for resuming failed generations.
        
        Returns:
            The last completed step, or None if no steps completed
        """
        steps = list(GenerationStep)
        last_completed = None
        
        for step in steps:
            step_data = self.generation_state.get(step.value, {})
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
        self.status = VideoStatus.FAILED
        self.error_log = {
            "message": error_message,
            "details": error_details or {},
            "step": self.current_step.value if self.current_step else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

