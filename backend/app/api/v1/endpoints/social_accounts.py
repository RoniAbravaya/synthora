"""
Social Account API Endpoints

Handles social media account connections and OAuth flows.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import get_settings
from app.services.social_oauth import SocialOAuthService
from app.integrations.social import get_platform_client
from app.models.user import User
from app.models.social_account import SocialAccount, SocialPlatform, AccountStatus
from app.schemas.social_account import (
    SocialAccountResponse,
    SocialAccountListResponse,
    OAuthInitResponse,
    OAuthCallbackRequest,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-accounts", tags=["Social Accounts"])

settings = get_settings()


# =============================================================================
# List Accounts
# =============================================================================

@router.get("", response_model=SocialAccountListResponse)
async def list_social_accounts(
    platform: Optional[SocialPlatform] = Query(default=None),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all connected social accounts for the current user.
    
    **Query Parameters:**
    - `platform`: Filter by platform (youtube, tiktok, instagram, facebook)
    
    **Requires:** Authentication
    """
    oauth_service = SocialOAuthService(db)
    accounts = oauth_service.get_user_accounts(user.id, platform)
    
    return SocialAccountListResponse(
        accounts=[_account_to_response(a) for a in accounts],
        total=len(accounts),
    )


@router.get("/{account_id}", response_model=SocialAccountResponse)
async def get_social_account(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific social account.
    
    **Path Parameters:**
    - `account_id`: UUID of the social account
    
    **Requires:** Authentication (must own the account)
    """
    oauth_service = SocialOAuthService(db)
    account = oauth_service.get_account_by_id(account_id)
    
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
    
    return _account_to_response(account)


# =============================================================================
# OAuth Flow
# =============================================================================

@router.post("/connect/{platform}", response_model=OAuthInitResponse)
async def initiate_oauth(
    platform: SocialPlatform,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Initiate OAuth flow for a social platform.
    
    Returns an authorization URL that the frontend should redirect the user to.
    
    **Path Parameters:**
    - `platform`: Social platform to connect
    
    **Requires:** Authentication
    """
    oauth_service = SocialOAuthService(db)
    
    # Generate redirect URI based on platform
    redirect_uri = _get_redirect_uri(platform)
    
    # Generate state for CSRF protection
    state = oauth_service.generate_oauth_state(user.id, platform, redirect_uri)
    
    # Get platform client and authorization URL
    client = get_platform_client(platform)
    auth_url = client.get_authorization_url(state=state)
    
    return OAuthInitResponse(
        authorization_url=auth_url,
        state=state,
        platform=platform,
    )


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: SocialPlatform,
    code: str = Query(..., description="Authorization code from OAuth"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    OAuth callback endpoint.
    
    This endpoint is called by the social platform after user authorization.
    
    **Path Parameters:**
    - `platform`: Social platform
    
    **Query Parameters:**
    - `code`: Authorization code
    - `state`: State parameter
    - `error`: Error code (if authorization failed)
    - `error_description`: Error description
    
    **Note:** This endpoint redirects to the frontend with success/error status.
    """
    oauth_service = SocialOAuthService(db)
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error for {platform.value}: {error} - {error_description}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/social?error={error}&platform={platform.value}"
        )
    
    # Validate state
    state_data = oauth_service.validate_oauth_state(state)
    if not state_data:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/social?error=invalid_state&platform={platform.value}"
        )
    
    user_id = UUID(state_data["user_id"])
    
    try:
        # Get platform client
        client = get_platform_client(platform)
        
        # Exchange code for tokens
        tokens = await client.exchange_code(code=code)
        
        if not tokens:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings/social?error=token_exchange_failed&platform={platform.value}"
            )
        
        # Get user profile from platform
        profile = await client.get_user_profile(tokens["access_token"])
        
        if not profile:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings/social?error=profile_fetch_failed&platform={platform.value}"
            )
        
        # Calculate token expiration
        from datetime import datetime, timedelta
        token_expires_at = None
        if tokens.get("expires_in"):
            token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        # Create or update account
        oauth_service.create_or_update_account(
            user_id=user_id,
            platform=platform,
            platform_user_id=profile.platform_user_id,
            username=profile.username,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=token_expires_at,
            profile_url=profile.profile_url,
            avatar_url=profile.avatar_url,
            metadata=profile.metadata,
        )
        
        await client.close()
        
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/social?success=true&platform={platform.value}"
        )
        
    except Exception as e:
        logger.exception(f"OAuth callback error for {platform.value}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/social?error=unknown&platform={platform.value}"
        )


@router.post("/callback/{platform}/manual", response_model=SocialAccountResponse)
async def oauth_callback_manual(
    platform: SocialPlatform,
    request: OAuthCallbackRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manual OAuth callback for SPAs.
    
    Use this endpoint if the frontend handles the OAuth redirect
    and sends the code back to the API.
    
    **Path Parameters:**
    - `platform`: Social platform
    
    **Request Body:**
    - `code`: Authorization code
    - `state`: State parameter
    
    **Requires:** Authentication
    """
    oauth_service = SocialOAuthService(db)
    
    # Validate state
    state_data = oauth_service.validate_oauth_state(request.state)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )
    
    if state_data["user_id"] != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="State does not match current user",
        )
    
    # Get platform client
    client = get_platform_client(platform)
    
    try:
        # Exchange code for tokens
        tokens = await client.exchange_code(code=request.code)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code",
            )
        
        # Get user profile
        profile = await client.get_user_profile(tokens["access_token"])
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user profile",
            )
        
        # Calculate token expiration
        from datetime import datetime, timedelta
        token_expires_at = None
        if tokens.get("expires_in"):
            token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        # Create or update account
        account = oauth_service.create_or_update_account(
            user_id=user.id,
            platform=platform,
            platform_user_id=profile.platform_user_id,
            username=profile.username,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=token_expires_at,
            profile_url=profile.profile_url,
            avatar_url=profile.avatar_url,
            metadata=profile.metadata,
        )
        
        return _account_to_response(account)
        
    finally:
        await client.close()


# =============================================================================
# Disconnect Account
# =============================================================================

@router.delete("/{account_id}", response_model=MessageResponse)
async def disconnect_account(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Disconnect a social account.
    
    **Path Parameters:**
    - `account_id`: UUID of the account to disconnect
    
    **Requires:** Authentication (must own the account)
    """
    oauth_service = SocialOAuthService(db)
    account = oauth_service.get_account_by_id(account_id)
    
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
    
    platform = account.platform.value
    username = account.username
    
    oauth_service.disconnect_account(account)
    
    return MessageResponse(
        message=f"Disconnected {platform} account: {username}"
    )


# =============================================================================
# Refresh Token
# =============================================================================

@router.post("/{account_id}/refresh", response_model=SocialAccountResponse)
async def refresh_account_token(
    account_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manually refresh an account's access token.
    
    **Path Parameters:**
    - `account_id`: UUID of the account
    
    **Requires:** Authentication (must own the account)
    """
    oauth_service = SocialOAuthService(db)
    account = oauth_service.get_account_by_id(account_id)
    
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
    
    # Force token refresh
    token = oauth_service.get_access_token(account)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refresh token. Please reconnect the account.",
        )
    
    # Refresh account from DB
    db.refresh(account)
    
    return _account_to_response(account)


# =============================================================================
# Helper Functions
# =============================================================================

def _account_to_response(account: SocialAccount) -> SocialAccountResponse:
    """Convert a SocialAccount model to response."""
    return SocialAccountResponse(
        id=account.id,
        platform=account.platform,
        username=account.username,
        profile_url=account.profile_url,
        avatar_url=account.avatar_url,
        status=account.status,
        scopes=account.scopes or [],
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
    )


def _get_redirect_uri(platform: SocialPlatform) -> str:
    """Get the OAuth redirect URI for a platform."""
    base_url = settings.API_URL or f"http://localhost:{settings.PORT}"
    return f"{base_url}/api/v1/social-accounts/callback/{platform.value}"
