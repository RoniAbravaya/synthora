"""
AI Suggestion Pydantic Schemas

Request and response schemas for AI suggestion-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.ai_suggestion import SuggestionType, SuggestionPriority


# =============================================================================
# Response Schemas
# =============================================================================

class SuggestionResponse(IDSchema, TimestampSchema):
    """Full AI suggestion response."""
    
    suggestion_type: str
    title: str
    description: str
    priority: str
    action_type: Optional[str] = None
    action_data: Dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    is_dismissed: bool
    is_acted: bool = False
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    acted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    related_video_id: Optional[UUID] = None
    related_post_id: Optional[UUID] = None
    related_template_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SuggestionListItem(BaseSchema):
    """Suggestion list item (condensed)."""
    
    id: UUID
    suggestion_type: str
    title: str
    description: str
    priority: str
    is_read: bool
    action_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class SuggestionListResponse(BaseSchema):
    """List of AI suggestions."""
    
    suggestions: List[SuggestionListItem]
    total: int
    unread_count: int


class UnreadCountResponse(BaseSchema):
    """Unread suggestions count."""
    
    count: int


class PostingTimeAnalysis(BaseSchema):
    """Posting time analysis result."""
    
    best_day: str
    best_day_index: int
    best_hour: int
    potential_improvement: float
    current_avg_engagement: float
    best_avg_engagement: float


class PostingTimeResponse(BaseSchema):
    """Posting time analysis response."""
    
    success: bool
    posts_analyzed: int
    period_days: int
    overall: Optional[PostingTimeAnalysis] = None
    by_platform: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ContentIdea(BaseSchema):
    """Content idea from AI."""
    
    topic: str
    hook: str
    description: str
    suggested_hashtags: List[str] = Field(default_factory=list)
    estimated_engagement: str


class ContentIdeasResponse(BaseSchema):
    """Content ideas response."""
    
    ideas: List[ContentIdea]


class TrendItem(BaseSchema):
    """Trending topic item."""
    
    topic: str
    description: str
    platforms: List[str] = Field(default_factory=list)
    virality_score: int
    suggested_angle: str
    relevance_score: Optional[float] = None


class TrendsResponse(BaseSchema):
    """Trends response."""
    
    trends: List[TrendItem]


class PerformancePrediction(BaseSchema):
    """Performance prediction for a video."""
    
    video_id: str
    predictions: Dict[str, Any]
    total_predicted_views: int
    avg_predicted_engagement: float
    confidence: float
    factors: List[str]
    based_on_posts: int


class PerformancePredictionResponse(BaseSchema):
    """Performance prediction response."""
    
    success: bool
    prediction: Optional[PerformancePrediction] = None
    error: Optional[str] = None


class ImprovementItem(BaseSchema):
    """Improvement suggestion item."""
    
    category: str
    issue: str
    suggestion: str
    impact: str


class UnderperformingPost(BaseSchema):
    """Underperforming post with improvements."""
    
    post_id: str
    title: Optional[str] = None
    current_engagement: float
    improvements: List[ImprovementItem]


class ImprovementsResponse(BaseSchema):
    """Improvements analysis response."""
    
    underperforming_posts: List[UnderperformingPost]


class GenerateSuggestionsResponse(BaseSchema):
    """Response for suggestions generation."""
    
    message: str
    job_id: Optional[str] = None
    estimated_time: Optional[str] = None


# =============================================================================
# Request Schemas
# =============================================================================

class MarkReadRequest(BaseSchema):
    """Request to mark suggestion as read."""
    
    pass  # No additional fields needed


class DismissRequest(BaseSchema):
    """Request to dismiss suggestion."""
    
    reason: Optional[str] = Field(default=None, description="Optional dismissal reason")


class GenerateSuggestionsRequest(BaseSchema):
    """Request to generate specific types of suggestions."""
    
    types: Optional[List[str]] = Field(
        default=None,
        description="Types of suggestions to generate (posting_time, content, trends, improvements). If empty, generates all."
    )

