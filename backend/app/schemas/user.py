"""
User Pydantic Schemas

Request and response schemas for user-related endpoints.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from app.schemas.common import BaseSchema, TimestampSchema, IDSchema
from app.models.user import UserRole


# =============================================================================
# Base Schemas
# =============================================================================

class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(description="User's email address")
    name: Optional[str] = Field(default=None, max_length=255, description="Display name")
    avatar_url: Optional[str] = Field(default=None, description="Profile picture URL")


# =============================================================================
# Request Schemas
# =============================================================================

class UserCreate(UserBase):
    """Schema for creating a new user (internal use)."""
    
    firebase_uid: str = Field(min_length=1, max_length=128, description="Firebase UID")


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""
    
    name: Optional[str] = Field(default=None, max_length=255, description="Display name")
    avatar_url: Optional[str] = Field(default=None, description="Profile picture URL")


class RoleUpdate(BaseSchema):
    """Schema for updating user role (admin only)."""
    
    role: UserRole = Field(description="New user role")


class StatusUpdate(BaseSchema):
    """Schema for updating user status (admin only)."""
    
    is_active: bool = Field(description="Whether the account is active")


# =============================================================================
# Response Schemas
# =============================================================================

class UserResponse(UserBase, IDSchema, TimestampSchema):
    """Full user response schema."""
    
    role: UserRole = Field(description="User role")
    is_active: bool = Field(description="Whether account is active")
    last_login_at: Optional[datetime] = Field(default=None, description="Last login timestamp")


class UserProfileResponse(UserResponse):
    """User profile with additional details."""
    
    # Subscription info
    subscription_plan: Optional[str] = Field(default=None, description="Current subscription plan")
    subscription_status: Optional[str] = Field(default=None, description="Subscription status")
    
    # Feature access
    can_schedule: bool = Field(description="Can user schedule posts")
    can_access_ai_suggestions: bool = Field(description="Can user access AI suggestions")
    daily_video_limit: Optional[int] = Field(default=None, description="Daily video limit (null=unlimited)")
    
    # Stats
    videos_count: int = Field(default=0, description="Total videos created")
    posts_count: int = Field(default=0, description="Total posts created")
    integrations_configured: int = Field(default=0, description="Number of integrations configured")


class UserListResponse(BaseSchema):
    """Paginated user list response."""
    
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


class UserStatsResponse(BaseSchema):
    """User statistics for admin dashboard."""
    
    total_users: int
    by_role: dict  # {"admin": 1, "premium": 10, "free": 100}
    active_users: int
    new_this_month: int


# =============================================================================
# Auth Schemas
# =============================================================================

class FirebaseTokenRequest(BaseSchema):
    """Request schema for Firebase token exchange."""
    
    id_token: str = Field(min_length=1, description="Firebase ID token")


class LoginResponse(BaseSchema):
    """Login response with user profile."""
    
    user: UserProfileResponse
    is_new_user: bool = Field(description="Whether this is a new registration")
    setup_required: bool = Field(description="Whether onboarding is required")


class SetupStatusResponse(BaseSchema):
    """Setup status response."""
    
    setup_completed: bool = Field(description="Whether initial setup is complete")
    message: str = Field(description="Status message")

