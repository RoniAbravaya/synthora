"""
Admin Pydantic Schemas

Request and response schemas for admin-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


# =============================================================================
# User Management Schemas
# =============================================================================

class AdminUserItem(BaseSchema):
    """User item for admin list."""
    
    id: UUID
    email: str
    display_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AdminUserListResponse(BaseSchema):
    """Admin user list response."""
    
    users: List[AdminUserItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class AdminUserStats(BaseSchema):
    """Stats for a specific user."""
    
    videos: int
    posts: int
    integrations: int
    social_accounts: int


class AdminUserDetailResponse(BaseSchema):
    """Detailed user information for admin."""
    
    id: UUID
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    stats: AdminUserStats


class UpdateUserRoleRequest(BaseSchema):
    """Request to update user role."""
    
    role: str = Field(description="New role (free, premium, admin)")


class UpdateUserStatusRequest(BaseSchema):
    """Request to update user status."""
    
    is_active: bool = Field(description="Active status")


class DeleteUserRequest(BaseSchema):
    """Request to delete user."""
    
    hard_delete: bool = Field(default=False, description="Permanently delete user and all data")


# =============================================================================
# Platform Statistics Schemas
# =============================================================================

class UserStats(BaseSchema):
    """User statistics."""
    
    total: int
    active: int
    new_30d: int
    by_role: Dict[str, int]


class VideoStats(BaseSchema):
    """Video generation statistics."""
    
    total: int
    by_status: Dict[str, int]


class PostStats(BaseSchema):
    """Post statistics."""
    
    total: int
    by_status: Dict[str, int]


class SubscriptionStats(BaseSchema):
    """Subscription statistics."""
    
    total: int
    active: int
    by_plan: Dict[str, int]
    mrr: float = Field(description="Monthly Recurring Revenue")
    arr: float = Field(description="Annual Recurring Revenue")


class PlatformStatsResponse(BaseSchema):
    """Platform-wide statistics."""
    
    users: UserStats
    videos: VideoStats
    posts: PostStats
    subscriptions: SubscriptionStats


class DailyDataPoint(BaseSchema):
    """Daily data point for charts."""
    
    date: str
    count: int


class ActivityStatsResponse(BaseSchema):
    """Activity statistics over time."""
    
    period_days: int
    daily_signups: List[DailyDataPoint]
    daily_videos: List[DailyDataPoint]
    daily_posts: List[DailyDataPoint]


class TopUserItem(BaseSchema):
    """Top user item."""
    
    user_id: str
    email: str
    display_name: Optional[str] = None
    role: str
    count: int


class TopUsersResponse(BaseSchema):
    """Top users by metric."""
    
    metric: str
    users: List[TopUserItem]


# =============================================================================
# System Settings Schemas
# =============================================================================

class SettingItem(BaseSchema):
    """Single setting item."""
    
    key: str
    value: Any
    description: Optional[str] = None


class SettingsResponse(BaseSchema):
    """All settings response."""
    
    settings: Dict[str, Any]


class SetSettingRequest(BaseSchema):
    """Request to set a setting."""
    
    key: str = Field(min_length=1, max_length=100, description="Setting key")
    value: Any = Field(description="Setting value")
    description: Optional[str] = Field(default=None, max_length=500, description="Setting description")


class FeatureFlags(BaseSchema):
    """Feature flag settings."""
    
    ai_suggestions: bool = True
    scheduling: bool = True
    analytics: bool = True
    video_generation: bool = True
    social_posting: bool = True


class SystemLimits(BaseSchema):
    """System limit settings."""
    
    free_videos_per_day: int = 1
    free_retention_days: int = 30
    rate_limit_per_minute: int = 100
    max_video_duration: int = 300


# =============================================================================
# Template Statistics
# =============================================================================

class TemplateUsageItem(BaseSchema):
    """Template usage item."""
    
    id: str
    name: str
    usage_count: int


class TemplateStatsResponse(BaseSchema):
    """Template statistics."""
    
    total: int
    system: int
    user_created: int
    most_used: List[TemplateUsageItem]


# =============================================================================
# Content Management
# =============================================================================

class RecentVideoItem(BaseSchema):
    """Recent video item."""
    
    id: UUID
    title: Optional[str] = None
    status: str
    user_id: UUID
    user_email: Optional[str] = None
    created_at: datetime


class RecentPostItem(BaseSchema):
    """Recent post item."""
    
    id: UUID
    title: Optional[str] = None
    status: str
    platforms: List[str]
    user_id: UUID
    user_email: Optional[str] = None
    created_at: datetime


class FailedJobItem(BaseSchema):
    """Failed job item."""
    
    id: UUID
    job_type: str
    error_message: Optional[str] = None
    user_id: Optional[UUID] = None
    created_at: datetime

