"""
Analytics Pydantic Schemas

Request and response schemas for analytics-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema


# =============================================================================
# Request Schemas
# =============================================================================

class AnalyticsSyncRequest(BaseSchema):
    """Request to sync analytics for specific posts."""
    
    post_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific post IDs to sync. If empty, syncs all posts."
    )


class TimeSeriesRequest(BaseSchema):
    """Request for time series data."""
    
    metric: str = Field(
        default="views",
        description="Metric to retrieve (views, likes, comments, shares)"
    )
    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back"
    )
    platform: Optional[str] = Field(
        default=None,
        description="Filter by platform"
    )


# =============================================================================
# Response Schemas
# =============================================================================

class AnalyticsMetrics(BaseSchema):
    """Core analytics metrics."""
    
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    watch_time_seconds: int = 0
    avg_view_duration: float = 0.0
    retention_rate: float = 0.0
    saves: int = 0
    click_through_rate: float = 0.0
    reach: int = 0
    impressions: int = 0
    follower_change: int = 0
    engagement_count: int = 0
    engagement_rate: float = 0.0


class AnalyticsResponse(IDSchema, AnalyticsMetrics):
    """Full analytics response for a post."""
    
    post_id: UUID
    platform: str
    fetched_at: datetime


class SummaryMetrics(BaseSchema):
    """Summary metrics for overview."""
    
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0


class OverviewResponse(BaseSchema):
    """Dashboard overview statistics."""
    
    period_days: int = 30
    total_posts: int = 0
    summary: SummaryMetrics
    by_platform: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    
    # Comparison with previous period
    views_change: Optional[float] = None
    likes_change: Optional[float] = None
    engagement_change: Optional[float] = None


class PlatformMetrics(BaseSchema):
    """Metrics for a specific platform."""
    
    platform: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0


class PlatformComparisonResponse(BaseSchema):
    """Platform comparison data."""
    
    period_days: int = 30
    platforms: List[PlatformMetrics]


class PostMetrics(BaseSchema):
    """Metrics for a single post."""
    
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class TopPerformingItem(BaseSchema):
    """Top performing post/video."""
    
    post_id: str
    video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    platforms: List[str] = Field(default_factory=list)
    published_at: Optional[str] = None
    metrics: PostMetrics


class TopPerformingResponse(BaseSchema):
    """Top performing content."""
    
    metric: str
    limit: int
    items: List[TopPerformingItem]


class TimeSeriesDataPoint(BaseSchema):
    """Single data point in time series."""
    
    date: str
    value: int


class TimeSeriesResponse(BaseSchema):
    """Time series data for charts."""
    
    metric: str
    days: int
    platform: Optional[str] = None
    data_points: List[TimeSeriesDataPoint]


class HeatmapHourData(BaseSchema):
    """Heatmap data for a single hour."""
    
    posts: int = 0
    avg_engagement: float = 0.0


class HeatmapResponse(BaseSchema):
    """Posting time heatmap data."""
    
    period_days: int = 90
    heatmap: Dict[str, Dict[str, HeatmapHourData]]
    best_times: Optional[List[Dict[str, Any]]] = None


class ChannelMetrics(BaseSchema):
    """Channel/account level metrics."""
    
    platform: str
    data: Dict[str, Any]


class ChannelAnalyticsResponse(BaseSchema):
    """Channel analytics for all platforms."""
    
    channels: List[ChannelMetrics]


class SyncResponse(BaseSchema):
    """Analytics sync response."""
    
    message: str
    job_id: Optional[str] = None
    estimated_time: Optional[str] = None


class PostAnalyticsResponse(BaseSchema):
    """Analytics for a specific post."""
    
    post_id: str
    platforms: Dict[str, AnalyticsMetrics]
    total: AnalyticsMetrics
    last_synced: Optional[datetime] = None

