"""
Social Account API Endpoints

Handles social media account connections and OAuth flows.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import get_settings
from app.core.security import encrypt_value
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
    
    Returns an authorization URL that the frontend should redirect the user to.
    
    **Note:** Returns an error if OAuth is not configured for this platform.
    """
    import secrets
    import urllib.parse
    
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
    
    # Generate state for CSRF protection (includes user_id for callback)
    # Format: random_token:user_id
    random_token = secrets.token_urlsafe(32)
    state = f"{random_token}:{user.id}"
    
    # Build redirect URI using the configured backend URL
    redirect_uri = settings.youtube_redirect_uri if platform == "youtube" else \
                   settings.tiktok_redirect_uri if platform == "tiktok" else \
                   settings.instagram_redirect_uri if platform == "instagram" else \
                   settings.facebook_redirect_uri
    
    # Build the authorization URL based on platform
    if platform == "youtube":
        # Google OAuth 2.0 for YouTube
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": oauth_config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": " ".join(oauth_config["scopes"]),
            "state": state,
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
    else:
        # Other platforms
        base_urls = {
            "tiktok": "https://www.tiktok.com/auth/authorize/",
            "instagram": "https://api.instagram.com/oauth/authorize",
            "facebook": "https://www.facebook.com/v18.0/dialog/oauth",
        }
        base_url = base_urls[platform]
        params = {
            "client_id": oauth_config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": " ".join(oauth_config["scopes"]),
            "state": state,
            "response_type": "code",
        }
    
    auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    logger.info(f"Generated OAuth URL for {platform}, user {user.id}")
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "platform": platform,
    }


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(default=None, description="Authorization code from OAuth"),
    state: str = Query(default=None, description="State parameter for CSRF validation"),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    OAuth callback endpoint.
    
    This endpoint is called by the social platform after user authorization.
    Exchanges the authorization code for access and refresh tokens,
    then redirects to the frontend with success/error status.
    """
    frontend_url = settings.FRONTEND_URL
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error for {platform}: {error} - {error_description}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error={error}&platform={platform}"
        )
    
    # Validate required parameters
    if not code or not state:
        logger.error(f"Missing code or state in OAuth callback for {platform}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error=missing_params&platform={platform}"
        )
    
    # Extract user_id from state (format: random_token:user_id)
    try:
        _, user_id_str = state.rsplit(":", 1)
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid state format in OAuth callback: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error=invalid_state&platform={platform}"
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User not found for OAuth callback: {user_id}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error=user_not_found&platform={platform}"
        )
    
    # Get OAuth config
    oauth_config = get_oauth_config(platform)
    if not oauth_config:
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error=oauth_not_configured&platform={platform}"
        )
    
    # Get redirect URI
    redirect_uri = settings.youtube_redirect_uri if platform == "youtube" else \
                   settings.tiktok_redirect_uri if platform == "tiktok" else \
                   settings.instagram_redirect_uri if platform == "instagram" else \
                   settings.facebook_redirect_uri
    
    try:
        async with httpx.AsyncClient() as client:
            if platform == "youtube":
                # Exchange code for tokens with Google
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": oauth_config["client_id"],
                        "client_secret": oauth_config["client_secret"],
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                
                if token_response.status_code != 200:
                    logger.error(f"YouTube token exchange failed: {token_response.status_code} - {token_response.text}")
                    return RedirectResponse(
                        url=f"{frontend_url}/settings/social?error=token_exchange_failed&platform={platform}"
                    )
                
                token_data = token_response.json()
                access_token = token_data["access_token"]
                refresh_token = token_data.get("refresh_token")  # May not be present on re-auth
                expires_in = token_data.get("expires_in", 3600)
                token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info(f"YouTube token exchange successful. Refresh token present: {refresh_token is not None}")
                
                # Get YouTube channel info
                channel_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "part": "snippet,statistics",
                        "mine": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                
                if channel_response.status_code != 200:
                    logger.error(f"YouTube channel fetch failed: {channel_response.status_code} - {channel_response.text}")
                    return RedirectResponse(
                        url=f"{frontend_url}/settings/social?error=channel_fetch_failed&platform={platform}"
                    )
                
                channel_data = channel_response.json()
                
                if not channel_data.get("items"):
                    return RedirectResponse(
                        url=f"{frontend_url}/settings/social?error=no_channel&platform={platform}"
                    )
                
                channel = channel_data["items"][0]
                channel_id = channel["id"]
                channel_title = channel["snippet"]["title"]
                channel_thumbnail = channel["snippet"]["thumbnails"]["default"]["url"]
                profile_url = f"https://youtube.com/channel/{channel_id}"
                
                # Check if account already exists
                existing_account = db.query(SocialAccount).filter(
                    SocialAccount.user_id == user.id,
                    SocialAccount.platform == platform,
                    SocialAccount.platform_user_id == channel_id,
                ).first()
                
                # Encrypt tokens
                encrypted_access = encrypt_value(access_token)
                encrypted_refresh = encrypt_value(refresh_token) if refresh_token else None
                
                if existing_account:
                    # Update existing account
                    existing_account.username = channel_title
                    existing_account.display_name = channel_title
                    existing_account.avatar_url = channel_thumbnail
                    existing_account.profile_url = profile_url
                    existing_account.access_token_encrypted = encrypted_access
                    # Only update refresh token if we got a new one
                    if encrypted_refresh:
                        existing_account.refresh_token_encrypted = encrypted_refresh
                    existing_account.token_expires_at = token_expires_at
                    existing_account.scopes = oauth_config["scopes"]
                    existing_account.status = "connected"
                    existing_account.is_active = True
                    
                    db.commit()
                    logger.info(f"Updated YouTube account for user {user.id}: {channel_title}")
                else:
                    # Create new account
                    new_account = SocialAccount(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        platform=platform,
                        platform_user_id=channel_id,
                        username=channel_title,
                        display_name=channel_title,
                        avatar_url=channel_thumbnail,
                        profile_url=profile_url,
                        access_token_encrypted=encrypted_access,
                        refresh_token_encrypted=encrypted_refresh,
                        token_expires_at=token_expires_at,
                        scopes=oauth_config["scopes"],
                        status="connected",
                        is_active=True,
                    )
                    
                    db.add(new_account)
                    db.commit()
                    logger.info(f"Created YouTube account for user {user.id}: {channel_title}")
                
                # Redirect to frontend with success
                return RedirectResponse(
                    url=f"{frontend_url}/settings/social?success=true&platform={platform}&account={channel_title}"
                )
            
            else:
                # Other platforms - not yet fully implemented
                return RedirectResponse(
                    url=f"{frontend_url}/settings/social?error=platform_not_implemented&platform={platform}"
                )
    
    except Exception as e:
        logger.exception(f"OAuth callback error for {platform}: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/social?error=server_error&platform={platform}"
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
    
    This will also remove any posts and analytics associated with this account.
    """
    from app.models.post import Post
    from app.models.analytics import Analytics
    
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
    
    try:
        # Get all post IDs for this social account
        post_ids = [p.id for p in db.query(Post.id).filter(Post.social_account_id == account_id).all()]
        
        if post_ids:
            # Delete analytics for these posts first
            db.query(Analytics).filter(Analytics.post_id.in_(post_ids)).delete(synchronize_session=False)
            
            # Delete the posts
            db.query(Post).filter(Post.social_account_id == account_id).delete(synchronize_session=False)
        
        # Now delete the social account
        db.delete(account)
        db.commit()
        
        logger.info(f"User {user.id} disconnected {platform} account: {username}")
        
        return {
            "message": f"Disconnected {platform} account: {username}"
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to disconnect social account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect account: {str(e)}",
        )


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
