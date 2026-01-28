"""
Video Actions Schemas

Pydantic schemas for video action API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class GenerateNowRequest(BaseModel):
    """Request to trigger immediate generation for a scheduled video."""
    # No additional fields needed - video ID comes from path
    pass


class GenerateNowResponse(BaseModel):
    """Response after triggering generation."""
    success: bool
    video_id: str
    message: str
    job_id: Optional[str] = None


class CancelVideoRequest(BaseModel):
    """Request to cancel a video generation."""
    reason: Optional[str] = Field(None, description="Optional cancellation reason")


class CancelVideoResponse(BaseModel):
    """Response after cancelling a video."""
    success: bool
    video_id: str
    message: str


class RetryVideoRequest(BaseModel):
    """Request to retry a failed video generation."""
    swap_providers: Optional[Dict[str, str]] = Field(
        None,
        description="Optional provider swaps: {category: new_provider}"
    )


class RetryVideoResponse(BaseModel):
    """Response after triggering retry."""
    success: bool
    video_id: str
    message: str
    job_id: Optional[str] = None


class RescheduleVideoRequest(BaseModel):
    """Request to reschedule a planned video."""
    scheduled_post_time: datetime = Field(
        ..., description="New scheduled post time"
    )


class RescheduleVideoResponse(BaseModel):
    """Response after rescheduling."""
    success: bool
    video_id: str
    new_scheduled_time: str
    message: str


class EditVideoRequest(BaseModel):
    """Request to edit a planned video's details."""
    title: Optional[str] = Field(None, description="New video title")
    prompt: Optional[str] = Field(None, description="New video prompt")
    template_id: Optional[str] = Field(None, description="New template ID")
    target_platforms: Optional[List[str]] = Field(
        None, description="New target platforms"
    )


class EditVideoResponse(BaseModel):
    """Response after editing video."""
    success: bool
    video_id: str
    message: str


class ScheduledVideoResponse(BaseModel):
    """Response for a scheduled video."""
    id: str
    title: Optional[str]
    prompt: str
    scheduled_post_time: Optional[str]
    planning_status: str
    target_platforms: Optional[List[str]]
    template_id: Optional[str]
    series_name: Optional[str]
    series_order: Optional[int]
    created_at: str


class ScheduledVideosListResponse(BaseModel):
    """Response for list of scheduled videos."""
    videos: List[ScheduledVideoResponse]
    total: int


class VideoGenerationStatus(BaseModel):
    """Detailed status of a video generation."""
    video_id: str
    status: str
    progress: int
    current_step: Optional[str]
    generation_started_at: Optional[str]
    last_step_updated_at: Optional[str]
    error_message: Optional[str]
    steps: Dict[str, Dict[str, Any]] = {}
    providers_used: Optional[List[str]] = None
