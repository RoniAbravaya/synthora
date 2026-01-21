"""
Social Account API Endpoints

Handles social media account connections and OAuth flows.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import get_settings
from app.models.user import User
from app.models.social_account import SocialAccount, SocialPlatform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-accounts", tags=["Social Accounts"])

settings = get_settings()


# =============================================================================
# Request Models
# =============================================================================

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


# =============================================================================
# Helper Functions
# =============================================================================

def account_to_response(account: SocialAccount) -> Dict[str, Any]:
    """Convert a SocialAccount model to response."""
    return {
        "id": str(account.id),
        "platform": account.platform,
        "platform_user_id": account.platform_user_id,
        "platform_username": account.username,
        "is_active": account.is_active,
        "status": account.status,
        "token_expires_at": str(account.token_expires_at) if account.token_expires_at else None,
        "created_at": str(account.created_at) if account.created_at else None,
    }


def get_oauth_config(platform: str) -> Optional[Dict[str, Any]]:
    """
    Get OAuth configuration for a platform.
    
    Returns None if not configured (missing credentials).
    """
    configs = {
        "youtube": {
            "client_id": getattr(settings, "YOUTUBE_CLIENT_ID", None),
            "client_secret": getattr(settings, "YOUTUBE_CLIENT_SECRET", None),
            "scopes": ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"],
        },
        "tiktok": {
            "client_id": getattr(settings, "TIKTOK_CLIENT_ID", None),
            "client_secret": getattr(settings, "TIKTOK_CLIENT_SECRET", None),
            "scopes": ["user.info.basic", "video.upload", "video.list"],
        },
        "instagram": {
            "client_id": getattr(settings, "INSTAGRAM_CLIENT_ID", None),
            "client_secret": getattr(settings, "INSTAGRAM_CLIENT_SECRET", None),
            "scopes": ["instagram_basic", "instagram_content_publish"],
        },
        "facebook": {
            "client_id": getattr(settings, "FACEBOOK_CLIENT_ID", None),
            "client_secret": getattr(settings, "FACEBOOK_CLIENT_SECRET", None),
            "scopes": ["pages_manage_posts", "pages_read_engagement"],
        },
    }
    
    config = configs.get(platform)
    if not config:
        return None
    
    # Check if credentials are configured
    if not config["client_id"] or not config["client_secret"]:
        return None
    
    return config


# =============================================================================
# List Accounts
# =============================================================================

@router.get("")
async def list_social_accounts(
    platform: Optional[str] = Query(default=None),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all connected social accounts for the current user.
    """
    query = db.query(SocialAccount).filter(
        SocialAccount.user_id == user.id
    )
    
    if platform:
        query = query.filter(SocialAccount.platform == platform)
    
    accounts = query.order_by(SocialAccount.created_at.desc()).all()
    
    return {
        "accounts": [account_to_response(a) for a in accounts],
        "total": len(accounts),
    }


@router.get("/{account_id}")
async def get_social_account(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific social account.
    """
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found",
        )
    
    if account.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this account",
        )
    
    return account_to_response(account)


# =============================================================================
# OAuth Flow
# =============================================================================

@router.post("/connect/{platform}")
async def initiate_oauth(
    platform: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Initiate OAuth flow for a social platform.
    
    Returns an authorization URL that the frontend should redirect the user to.
    
    **Note:** Returns an error if OAuth is not configured for this platform.
    """
    # Validate platform
    valid_platforms = ["youtube", "tiktok", "instagram", "facebook"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )
    
    # Check if OAuth is configured
    oauth_config = get_oauth_config(platform)
    if not oauth_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth for {platform} is not configured. Please contact the administrator to set up {platform} integration.",
        )
    
    # Build the authorization URL
    # This is a simplified version - in production, you'd use the actual OAuth library
    base_urls = {
        "youtube": "https://accounts.google.com/o/oauth2/v2/auth",
        "tiktok": "https://www.tiktok.com/auth/authorize/",
        "instagram": "https://api.instagram.com/oauth/authorize",
        "facebook": "https://www.facebook.com/v18.0/dialog/oauth",
    }
    
    import secrets
    import urllib.parse
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Build redirect URI
    api_url = getattr(settings, "API_URL", None) or f"http://localhost:{getattr(settings, 'PORT', 8000)}"
    redirect_uri = f"{api_url}/api/v1/social-accounts/callback/{platform}"
    
    # Build authorization URL
    params = {
        "client_id": oauth_config["client_id"],
        "redirect_uri": redirect_uri,
        "scope": " ".join(oauth_config["scopes"]),
        "state": state,
        "response_type": "code",
    }
    
    # Platform-specific params
    if platform == "youtube":
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    
    auth_url = f"{base_urls[platform]}?{urllib.parse.urlencode(params)}"
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "platform": platform,
    }


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(..., description="Authorization code from OAuth"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    OAuth callback endpoint.
    
    This endpoint is called by the social platform after user authorization.
    Redirects to the frontend with success/error status.
    """
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error for {platform}: {error} - {error_description}")
        return RedirectResponse(
            url=f"{frontend_url}/social-accounts?error={error}&platform={platform}"
        )
    
    # For now, redirect with a message that OAuth is not fully implemented
    # In production, you would:
    # 1. Validate the state
    # 2. Exchange the code for tokens
    # 3. Get the user profile
    # 4. Create/update the social account
    
    return RedirectResponse(
        url=f"{frontend_url}/social-accounts?error=oauth_not_configured&platform={platform}"
    )


@router.post("/callback/{platform}/manual")
async def oauth_callback_manual(
    platform: str,
    request: OAuthCallbackRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manual OAuth callback for SPAs.
    
    Use this endpoint if the frontend handles the OAuth redirect
    and sends the code back to the API.
    """
    # Check if OAuth is configured
    oauth_config = get_oauth_config(platform)
    if not oauth_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth for {platform} is not configured",
        )
    
    # In production, you would exchange the code for tokens here
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth token exchange for {platform} is not yet implemented",
    )


# =============================================================================
# Disconnect Account
# =============================================================================

@router.delete("/{account_id}")
async def disconnect_account(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Disconnect a social account.
    """
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found",
        )
    
    if account.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to disconnect this account",
        )
    
    platform = account.platform
    username = account.username
    
    db.delete(account)
    db.commit()
    
    return {
        "message": f"Disconnected {platform} account: {username}"
    }


# =============================================================================
# Refresh Token
# =============================================================================

@router.post("/{account_id}/refresh")
async def refresh_account_token(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manually refresh an account's access token.
    """
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found",
        )
    
    if account.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to refresh this account",
        )
    
    # In production, you would refresh the token here
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh is not yet implemented. Please reconnect the account.",
    )
