"""
Post Pydantic Schemas

Request and response schemas for post-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.post import PostStatus
from app.models.social_account import SocialPlatform


# =============================================================================
# Request Schemas
# =============================================================================

class PostCreate(BaseSchema):
    """Schema for creating a new post."""
    
    video_id: UUID = Field(description="Video to post")
    platforms: List[SocialPlatform] = Field(min_length=1, description="Platforms to post to")
    
    # Content
    title: Optional[str] = Field(default=None, max_length=255, description="Post title")
    description: Optional[str] = Field(default=None, max_length=5000, description="Post description/caption")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags")
    
    # Scheduling
    scheduled_at: Optional[datetime] = Field(default=None, description="Schedule time (None for draft)")
    
    # Platform-specific overrides
    platform_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Platform-specific settings by platform name"
    )


class PostUpdate(BaseSchema):
    """Schema for updating a post."""
    
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    hashtags: Optional[List[str]] = None
    platforms: Optional[List[SocialPlatform]] = None
    scheduled_at: Optional[datetime] = None
    platform_overrides: Optional[Dict[str, Dict[str, Any]]] = None


class PublishNowRequest(BaseSchema):
    """Request to publish a post immediately."""
    pass  # No additional fields needed


# =============================================================================
# Response Schemas
# =============================================================================

class PostResponse(IDSchema, TimestampSchema):
    """Full post response."""
    
    user_id: UUID
    video_id: UUID
    
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    
    platforms: List[str] = Field(default_factory=list)
    platform_status: Dict[str, Any] = Field(default_factory=dict)
    platform_overrides: Dict[str, Any] = Field(default_factory=dict)
    
    status: PostStatus
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Error info for failed posts
    error_message: Optional[str] = None
    post_url: Optional[str] = None
    platform_post_id: Optional[str] = None


class PostListResponse(BaseSchema):
    """Paginated post list."""
    
    posts: List[PostResponse]
    total: int
    skip: int
    limit: int


class CalendarDayItem(BaseSchema):
    """Post item for calendar day."""
    
    id: str
    video_id: str
    title: Optional[str] = None
    status: str
    platforms: List[str]
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None


class CalendarResponse(BaseSchema):
    """Calendar view data."""
    
    year: int
    month: int
    days: Dict[int, List[CalendarDayItem]] = Field(description="Posts grouped by day number")
    total_posts: int


class PostCreateResponse(BaseSchema):
    """Response after creating post(s)."""
    
    posts: List[PostResponse]
    message: str
    scheduled: bool = Field(description="Whether posts are scheduled")

