"""
AI Suggestion Data Pydantic Schemas

Schemas for AI-generated video suggestions including complete generation details,
series plans, and monthly content plans.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


# =============================================================================
# Core AI Suggestion Data
# =============================================================================

class AISuggestionData(BaseSchema):
    """
    Complete AI-generated suggestion data.
    
    Contains all the information needed to generate a video,
    including content, style, and platform recommendations.
    """
    
    # Core content
    title: str = Field(description="Compelling video title")
    description: str = Field(description="Detailed description of what the video covers")
    hook: str = Field(description="Attention-grabbing opening line/concept (first 3 seconds)")
    script_outline: str = Field(description="Bullet-point outline of the video script")
    
    # Metadata
    hashtags: List[str] = Field(default_factory=list, description="Hashtags for discovery")
    estimated_duration_seconds: int = Field(default=60, ge=5, le=600, description="Estimated video duration")
    
    # Style guidance
    visual_style: str = Field(description="Visual style description (e.g., 'modern, fast-paced, colorful')")
    tone: str = Field(description="Tone of the video (e.g., 'educational, friendly, energetic')")
    target_audience: str = Field(description="Target audience description")
    
    # Platform recommendations
    recommended_platforms: List[str] = Field(
        default_factory=list,
        description="Recommended platforms (youtube, tiktok, instagram, facebook)"
    )
    platform_specific_notes: Optional[Dict[str, str]] = Field(
        default=None,
        description="Platform-specific optimization notes"
    )
    
    # Generation context
    based_on_analytics: bool = Field(
        default=False,
        description="True if suggestion is based on user's analytics, False if trend-based"
    )
    source_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Analytics or trend data used to generate suggestion"
    )
    
    # Series info (if part of series)
    is_series: bool = Field(default=False, description="Whether this is part of a series")
    series_total_parts: Optional[int] = Field(default=None, description="Total parts in series")
    series_theme: Optional[str] = Field(default=None, description="Overall series theme")


class SmartSuggestionResponse(BaseSchema):
    """Response from the smart suggestion generation endpoint."""
    
    suggestion: AISuggestionData
    chat_session_id: UUID = Field(description="Chat session ID for follow-up conversation")
    data_source: str = Field(description="Source of suggestion: 'analytics' or 'trends'")
    data_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Statistics about user data (posts, days, engagement)"
    )


# =============================================================================
# Series and Monthly Plans
# =============================================================================

class ScheduleItem(BaseSchema):
    """A scheduled time for a video in a plan."""
    
    video_index: int = Field(ge=0, description="Index of the video in the plan (0-based)")
    scheduled_time: datetime = Field(description="When the video should be posted")
    target_platforms: List[str] = Field(
        default_factory=list,
        description="Platforms to post to"
    )


class VideoSeriesPlan(BaseSchema):
    """Plan for a video series."""
    
    series_name: str = Field(description="Name of the series")
    series_description: str = Field(description="Description of the series")
    total_parts: int = Field(ge=2, le=20, description="Total number of parts")
    videos: List[AISuggestionData] = Field(description="Individual video suggestions")
    schedule: List[ScheduleItem] = Field(description="Schedule for each video")


class MonthlyContentPlan(BaseSchema):
    """Monthly content plan with multiple videos."""
    
    month: str = Field(description="Month in format 'YYYY-MM' or 'February 2026'")
    plan_type: str = Field(description="Type: 'variety', 'single_series', or 'multiple_series'")
    total_videos: int = Field(ge=1, le=31, description="Total videos in the plan")
    videos: List[AISuggestionData] = Field(description="Individual video suggestions")
    schedule: List[ScheduleItem] = Field(description="Schedule for each video")
    series_info: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Series information if plan_type involves series"
    )


# =============================================================================
# Action Card Data
# =============================================================================

class SingleVideoActionData(BaseSchema):
    """Data for single video action card."""
    
    suggestion: AISuggestionData
    suggested_post_time: Optional[datetime] = None


class SeriesActionData(BaseSchema):
    """Data for series action card."""
    
    series_plan: VideoSeriesPlan


class MonthlyPlanActionData(BaseSchema):
    """Data for monthly plan action card."""
    
    monthly_plan: MonthlyContentPlan


class ScheduleActionData(BaseSchema):
    """Data for schedule action card."""
    
    suggestion: AISuggestionData
    proposed_time: datetime
    target_platforms: List[str]
