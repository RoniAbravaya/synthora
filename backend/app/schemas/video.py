"""
Video Pydantic Schemas

Request and response schemas for video-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Request Schemas
# =============================================================================

class VideoGenerateRequest(BaseSchema):
    """Request to generate a new video."""
    
    # Accept both 'prompt' and 'topic' for backwards compatibility
    prompt: Optional[str] = Field(default=None, max_length=2000, description="Main topic/prompt")
    topic: Optional[str] = Field(default=None, max_length=2000, description="Alias for prompt")
    template_id: Optional[UUID] = Field(default=None, description="Template to use")
    title: Optional[str] = Field(default=None, max_length=255, description="Video title")
    custom_instructions: Optional[str] = Field(default=None, max_length=1000, description="Custom instructions")
    
    # Optional configuration overrides
    config_overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration overrides for generation"
    )
    
    @model_validator(mode='after')
    def validate_prompt_or_topic(self) -> 'VideoGenerateRequest':
        """Ensure at least one of prompt or topic is provided."""
        if not self.prompt and not self.topic:
            raise ValueError("Either 'prompt' or 'topic' must be provided")
        # Normalize: if only topic is provided, copy it to prompt
        if not self.prompt and self.topic:
            self.prompt = self.topic
        return self


class VideoGenerationRequest(BaseSchema):
    """Request to generate a new video (alias)."""
    
    template_id: Optional[UUID] = Field(default=None, description="Template to use")
    prompt: str = Field(min_length=1, max_length=2000, description="Main topic/prompt")
    title: Optional[str] = Field(default=None, max_length=255, description="Video title")
    
    # Optional overrides
    duration: Optional[int] = Field(default=None, ge=5, le=300, description="Target duration in seconds")
    aspect_ratio: Optional[str] = Field(default=None, description="Aspect ratio override")
    
    # Integration preferences
    preferred_video_ai: Optional[str] = Field(default=None, description="Preferred video AI provider")
    preferred_assembly: Optional[str] = Field(default=None, description="Preferred assembly provider")


class VideoRetryRequest(BaseSchema):
    """Request to retry a failed video generation."""
    
    swap_integrations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Map of step name -> new provider to swap"
    )


class SwapIntegrationRequest(BaseSchema):
    """Request to swap integration and retry."""
    
    step: str = Field(description="Step to swap integration for")
    new_provider: str = Field(description="New provider to use")


# =============================================================================
# Response Schemas
# =============================================================================

class StepStatus(BaseSchema):
    """Status of a generation step."""
    
    status: str = Field(description="Step status (pending, processing, completed, failed)")
    progress: int = Field(default=0, ge=0, le=100, description="Step progress percentage")
    result: Optional[Any] = Field(default=None, description="Step result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class VideoStatusResponse(BaseSchema):
    """Real-time video generation status."""
    
    id: UUID
    status: str  # String, not enum
    progress: int = Field(ge=0, le=100, description="Overall progress percentage")
    current_step: Optional[str] = None  # String, not enum
    generation_state: Optional[Dict[str, Any]] = Field(default=None, description="Status of each step")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Full error details")


class VideoResponse(IDSchema, TimestampSchema):
    """Full video response."""
    
    user_id: UUID
    template_id: Optional[UUID] = None
    title: Optional[str] = None
    prompt: str
    
    status: str  # String, not enum
    progress: int = 0
    current_step: Optional[str] = None  # String, not enum
    
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    resolution: Optional[str] = None
    
    integrations_used: List[str] = Field(default_factory=list)
    generation_time_seconds: Optional[float] = None
    
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # Planning fields (for scheduled/AI-generated videos)
    planning_status: Optional[str] = Field(default=None, description="Planning status: none, planned, generating, ready, posting, posted, failed")
    scheduled_post_time: Optional[datetime] = Field(default=None, description="When the video should be posted")
    generation_triggered_at: Optional[datetime] = Field(default=None, description="When generation was triggered")
    posted_at: Optional[datetime] = Field(default=None, description="When the video was posted")
    series_name: Optional[str] = Field(default=None, description="Series name if part of a series")
    series_order: Optional[int] = Field(default=None, description="Order in the series")
    target_platforms: Optional[List[str]] = Field(default=None, description="Target platforms for posting")
    ai_suggestion_data: Optional[Dict[str, Any]] = Field(default=None, description="AI suggestion data")


class VideoListItem(IDSchema):
    """Simplified video for list views."""
    
    title: Optional[str] = None
    prompt: str
    status: str  # String, not enum
    progress: int
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class VideoListResponse(BaseSchema):
    """Paginated video list."""
    
    videos: List[VideoResponse]
    total: int
    skip: int
    limit: int


class VideoGenerationResponse(BaseSchema):
    """Response after starting video generation."""
    
    video_id: UUID
    job_id: UUID
    status: str  # String, not enum
    message: str
    estimated_time: str = Field(description="Estimated generation time")
