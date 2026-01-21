"""
Social Account Pydantic Schemas

Request and response schemas for social account-related endpoints.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.social_account import SocialPlatform, AccountStatus


# =============================================================================
# Response Schemas
# =============================================================================

class SocialAccountResponse(IDSchema):
    """Social account response."""
    
    platform: SocialPlatform
    username: str
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    status: AccountStatus
    scopes: List[str] = Field(default_factory=list)
    last_sync_at: Optional[datetime] = None
    created_at: datetime


class SocialAccountListResponse(BaseSchema):
    """List of connected social accounts."""
    
    accounts: List[SocialAccountResponse]
    total: int


class OAuthInitResponse(BaseSchema):
    """OAuth initiation response."""
    
    authorization_url: str = Field(description="URL to redirect user to")
    state: str = Field(description="State parameter for CSRF protection")
    platform: SocialPlatform


class OAuthCallbackResponse(BaseSchema):
    """OAuth callback result."""
    
    success: bool
    platform: str
    account_name: Optional[str] = None
    message: str


# =============================================================================
# Request Schemas
# =============================================================================

class OAuthCallbackRequest(BaseSchema):
    """Request for manual OAuth callback (SPA flow)."""
    
    code: str = Field(description="Authorization code from OAuth")
    state: str = Field(description="State parameter for CSRF validation")


class DisconnectRequest(BaseSchema):
    """Request to disconnect a social account."""
    
    revoke_access: bool = Field(default=True, description="Also revoke OAuth access")

