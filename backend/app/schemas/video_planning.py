"""
Video Planning Pydantic Schemas

Request and response schemas for video scheduling and planning endpoints.
Supports scheduling single videos, creating series, and monthly plans.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.schemas.ai_suggestion_data import (
    AISuggestionData,
    VideoSeriesPlan,
    MonthlyContentPlan,
    ScheduleItem,
)


# =============================================================================
# Request Schemas
# =============================================================================

class ScheduleVideoRequest(BaseSchema):
    """Request to schedule a single video."""
    
    suggestion_data: AISuggestionData = Field(
        description="Complete AI suggestion data for video generation"
    )
    scheduled_post_time: datetime = Field(
        description="When the video should be posted"
    )
    target_platforms: List[str] = Field(
        min_length=1,
        description="Platforms to post to (youtube, tiktok, instagram, facebook)"
    )
    
    # Optional series info
    series_name: Optional[str] = Field(default=None, description="Series name if part of series")
    series_order: Optional[int] = Field(default=None, ge=1, description="Order in series")
    
    @field_validator("target_platforms")
    @classmethod
    def validate_platforms(cls, v: List[str]) -> List[str]:
        valid_platforms = {"youtube", "tiktok", "instagram", "facebook"}
        for platform in v:
            if platform.lower() not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}. Must be one of: {valid_platforms}")
        return [p.lower() for p in v]


class CreateSeriesRequest(BaseSchema):
    """Request to create a video series."""
    
    series_name: str = Field(min_length=1, max_length=255, description="Series name")
    videos: List[AISuggestionData] = Field(
        min_length=2,
        max_length=20,
        description="Video suggestions for each part"
    )
    schedule: List[ScheduleItem] = Field(
        min_length=2,
        description="Schedule for each video"
    )
    target_platforms: List[str] = Field(
        min_length=1,
        description="Platforms to post to (same for all videos)"
    )
    
    @field_validator("schedule")
    @classmethod
    def validate_schedule_matches_videos(cls, v: List[ScheduleItem], info) -> List[ScheduleItem]:
        # Access videos from the validated data
        if "videos" in info.data:
            videos = info.data["videos"]
            if len(v) != len(videos):
                raise ValueError("Schedule must have same number of items as videos")
            # Check video indices
            indices = {item.video_index for item in v}
            expected = set(range(len(videos)))
            if indices != expected:
                raise ValueError(f"Schedule video_index values must be 0 to {len(videos)-1}")
        return v


class CreateMonthlyPlanRequest(BaseSchema):
    """Request to create a monthly content plan."""
    
    plan: MonthlyContentPlan = Field(description="Monthly content plan details")


class UpdatePlannedVideoRequest(BaseSchema):
    """Request to update a planned video."""
    
    # Scheduling changes
    scheduled_post_time: Optional[datetime] = Field(
        default=None,
        description="New scheduled post time"
    )
    target_platforms: Optional[List[str]] = Field(
        default=None,
        description="New target platforms"
    )
    
    # Content changes
    title: Optional[str] = Field(default=None, max_length=255)
    ai_suggestion_data: Optional[AISuggestionData] = Field(
        default=None,
        description="Updated suggestion data"
    )
    
    # Series changes
    series_name: Optional[str] = Field(default=None, max_length=255)
    series_order: Optional[int] = Field(default=None, ge=1)
    
    @field_validator("target_platforms")
    @classmethod
    def validate_platforms(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        valid_platforms = {"youtube", "tiktok", "instagram", "facebook"}
        for platform in v:
            if platform.lower() not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}")
        return [p.lower() for p in v]


# =============================================================================
# Response Schemas
# =============================================================================

class PlannedVideoResponse(IDSchema, TimestampSchema):
    """Response for a planned/scheduled video."""
    
    user_id: UUID
    title: Optional[str] = None
    prompt: Optional[str] = None
    
    # Planning status
    planning_status: str = Field(description="none, planned, generating, ready, posting, posted, failed")
    scheduled_post_time: Optional[datetime] = None
    generation_triggered_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    
    # Series info
    series_name: Optional[str] = None
    series_order: Optional[int] = None
    
    # Platforms
    target_platforms: List[str] = Field(default_factory=list)
    
    # AI suggestion data
    ai_suggestion_data: Optional[Dict[str, Any]] = None
    
    # Video details (if generated)
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    
    # Error info
    error_message: Optional[str] = None


class ScheduleVideoResponse(BaseSchema):
    """Response after scheduling a video."""
    
    video: PlannedVideoResponse
    message: str = "Video scheduled successfully"


class CreateSeriesResponse(BaseSchema):
    """Response after creating a video series."""
    
    series_name: str
    videos: List[PlannedVideoResponse]
    total_videos: int
    message: str = "Video series created successfully"


class CreateMonthlyPlanResponse(BaseSchema):
    """Response after creating a monthly plan."""
    
    month: str
    videos: List[PlannedVideoResponse]
    total_videos: int
    message: str = "Monthly plan created successfully"


class PlannedVideoListResponse(BaseSchema):
    """List of planned videos."""
    
    videos: List[PlannedVideoResponse]
    total: int
    
    # Group by series
    series: Optional[Dict[str, List[PlannedVideoResponse]]] = Field(
        default=None,
        description="Videos grouped by series name"
    )


class TriggerGenerationResponse(BaseSchema):
    """Response after triggering video generation."""
    
    message: str
    job_id: str
    video_id: UUID
    estimated_time: str = "5-15 minutes"


# =============================================================================
# Calendar View Schemas
# =============================================================================

class CalendarVideoItem(BaseSchema):
    """Video item for calendar view."""
    
    id: UUID
    title: Optional[str] = None
    planning_status: str
    scheduled_post_time: Optional[datetime] = None
    target_platforms: List[str] = Field(default_factory=list)
    series_name: Optional[str] = None
    series_order: Optional[int] = None
    thumbnail_url: Optional[str] = None
    
    # Computed for UI
    is_overdue: bool = Field(default=False, description="If scheduled time has passed")
    can_generate_now: bool = Field(default=False, description="If manual generation is possible")


class CalendarViewResponse(BaseSchema):
    """Response for calendar view of planned videos."""
    
    items: List[CalendarVideoItem]
    start_date: datetime
    end_date: datetime
    total_planned: int
    total_ready: int
    total_posted: int
    total_failed: int
