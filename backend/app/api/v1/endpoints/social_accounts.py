"""
Social Account API Endpoints

Handles social media account connections and OAuth flows.
"""

import logging
import uuid
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

class FirebaseConnectRequest(BaseModel):
    """Request model for Firebase-based OAuth connection."""
    access_token: str
    platform_user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None


@router.post("/connect/{platform}/firebase")
async def connect_with_firebase(
    platform: str,
    request: FirebaseConnectRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Connect a social account using Firebase OAuth.
    
    This endpoint receives the OAuth access token from Firebase (obtained via popup)
    and creates/updates the social account in the database.
    
    Currently supports: youtube (via Google OAuth)
    """
    # Validate platform
    firebase_platforms = ["youtube"]  # Platforms that use Firebase OAuth
    if platform not in firebase_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Firebase OAuth not supported for {platform}. Use redirect-based OAuth instead.",
        )
    
    # For YouTube, we need to verify the token and get channel info
    if platform == "youtube":
        try:
            import httpx
            
            # Get YouTube channel info to verify the token and get channel details
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "part": "snippet,contentDetails",
                        "mine": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {request.access_token}",
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid YouTube access token or insufficient permissions",
                    )
                
                data = response.json()
                
                if not data.get("items"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No YouTube channel found for this account",
                    )
                
                channel = data["items"][0]
                channel_id = channel["id"]
                channel_title = channel["snippet"]["title"]
                channel_thumbnail = channel["snippet"]["thumbnails"]["default"]["url"]
                
        except httpx.RequestError as e:
            logger.error(f"Failed to verify YouTube token: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to verify YouTube access token",
            )
    
    # Encrypt the access token for storage
    from app.core.security import encrypt_value
    encrypted_token = encrypt_value(request.access_token)
    
    # Check if account already exists
    existing_account = db.query(SocialAccount).filter(
        SocialAccount.user_id == user.id,
        SocialAccount.platform == platform,
        SocialAccount.platform_user_id == channel_id,
    ).first()
    
    if existing_account:
        # Update existing account
        existing_account.username = channel_title
        existing_account.display_name = channel_title
        existing_account.avatar_url = channel_thumbnail
        existing_account.access_token_encrypted = encrypted_token
        existing_account.status = "connected"
        existing_account.is_active = True
        
        db.commit()
        db.refresh(existing_account)
        
        logger.info(f"Updated YouTube account for user {user.id}: {channel_title}")
        
        return {
            "account": account_to_response(existing_account),
            "message": f"YouTube account '{channel_title}' reconnected successfully",
        }
    
    # Create new account
    import uuid
    
    new_account = SocialAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        platform=platform,
        platform_user_id=channel_id,
        username=channel_title,
        display_name=channel_title,
        avatar_url=channel_thumbnail,
        access_token_encrypted=encrypted_token,
        refresh_token_encrypted=None,  # Firebase doesn't provide refresh tokens
        scopes=["youtube.upload", "youtube.readonly"],
        status="connected",
        is_active=True,
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    logger.info(f"Created YouTube account for user {user.id}: {channel_title}")
    
    return {
        "account": account_to_response(new_account),
        "message": f"YouTube account '{channel_title}' connected successfully",
    }


@router.post("/connect/{platform}")
async def initiate_oauth(
    platform: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Initiate OAuth flow for a social platform (redirect-based).
    
    For YouTube, use the /connect/youtube/firebase endpoint instead.
    
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
    
    # For YouTube, recommend using Firebase OAuth
    if platform == "youtube":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube uses Firebase OAuth. Use the /connect/youtube/firebase endpoint or the frontend popup flow.",
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
