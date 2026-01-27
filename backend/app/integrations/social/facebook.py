"""
Facebook Integration

OAuth and API client for Facebook.
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlencode

import httpx

from app.integrations.social.base import (
    BaseSocialClient,
    OAuthConfig,
    UserProfile,
    PostResult,
    AnalyticsData,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FacebookClient(BaseSocialClient):
    """
    Facebook OAuth and API client.
    
    Uses Meta's Graph API for Facebook Pages.
    Note: Video posting requires a Facebook Page, not a personal profile.
    """
    
    # OAuth endpoints
    AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    # API endpoints
    GRAPH_API = "https://graph.facebook.com/v18.0"
    
    # Required scopes
    DEFAULT_SCOPES = [
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "pages_read_user_content",
        "publish_video",
    ]
    
    def __init__(self):
        """Initialize the Facebook client."""
        super().__init__()
        settings = get_settings()
        
        self.default_config = OAuthConfig(
            client_id=settings.META_APP_ID or "",
            client_secret=settings.META_APP_SECRET or "",
            redirect_uri=settings.facebook_redirect_uri,
            scopes=self.DEFAULT_SCOPES,
        )
    
    # =========================================================================
    # OAuth Methods
    # =========================================================================
    
    def get_authorization_url(
        self,
        config: Optional[OAuthConfig] = None,
        state: str = "",
    ) -> str:
        """Get the Facebook OAuth authorization URL."""
        config = config or self.default_config
        
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": ",".join(config.scopes),
            "state": state,
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        config: Optional[OAuthConfig] = None,
        code: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        config = config or self.default_config
        
        try:
            # Get short-lived token
            response = await self.client.get(
                self.TOKEN_URL,
                params={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Facebook token exchange failed: {response.text}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"Facebook token error: {data}")
                return None
            
            short_lived_token = data["access_token"]
            
            # Exchange for long-lived token
            long_lived_response = await self.client.get(
                f"{self.GRAPH_API}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "fb_exchange_token": short_lived_token,
                },
            )
            
            if long_lived_response.status_code != 200:
                return {
                    "access_token": short_lived_token,
                    "expires_in": data.get("expires_in", 3600),
                }
            
            long_data = long_lived_response.json()
            
            return {
                "access_token": long_data.get("access_token", short_lived_token),
                "expires_in": long_data.get("expires_in", 5184000),
                "token_type": "Bearer",
            }
            
        except Exception as e:
            logger.exception("Facebook token exchange error")
            return None
    
    async def refresh_access_token(
        self,
        config: Optional[OAuthConfig] = None,
        refresh_token: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        config = config or self.default_config
        
        try:
            response = await self.client.get(
                f"{self.GRAPH_API}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "fb_exchange_token": refresh_token,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Facebook token refresh failed: {response.text}")
                return None
            
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_in": data.get("expires_in", 5184000),
            }
            
        except Exception as e:
            logger.exception("Facebook token refresh error")
            return None
    
    # =========================================================================
    # Profile Methods
    # =========================================================================
    
    async def get_user_profile(
        self,
        access_token: str,
    ) -> Optional[UserProfile]:
        """Get the authenticated user's Facebook profile and pages."""
        try:
            # Get user info
            user_response = await self.client.get(
                f"{self.GRAPH_API}/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name,picture",
                },
            )
            
            if user_response.status_code != 200:
                logger.error(f"Facebook profile fetch failed: {user_response.text}")
                return None
            
            user_data = user_response.json()
            
            # Get pages managed by user
            pages_response = await self.client.get(
                f"{self.GRAPH_API}/me/accounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,access_token,fan_count,picture",
                },
            )
            
            pages = []
            if pages_response.status_code == 200:
                pages_data = pages_response.json()
                pages = pages_data.get("data", [])
            
            # Use first page if available, otherwise user profile
            if pages:
                page = pages[0]
                return UserProfile(
                    platform_user_id=page["id"],
                    username=page.get("name", ""),
                    display_name=page.get("name"),
                    profile_url=f"https://facebook.com/{page['id']}",
                    avatar_url=page.get("picture", {}).get("data", {}).get("url"),
                    followers_count=page.get("fan_count", 0),
                    metadata={
                        "type": "page",
                        "page_access_token": page.get("access_token"),
                        "all_pages": [{"id": p["id"], "name": p["name"]} for p in pages],
                    },
                )
            
            return UserProfile(
                platform_user_id=user_data["id"],
                username=user_data.get("name", ""),
                display_name=user_data.get("name"),
                profile_url=f"https://facebook.com/{user_data['id']}",
                avatar_url=user_data.get("picture", {}).get("data", {}).get("url"),
                metadata={"type": "user"},
            )
            
        except Exception as e:
            logger.exception("Facebook profile fetch error")
            return None
    
    # =========================================================================
    # Posting Methods
    # =========================================================================
    
    async def upload_video(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        page_id: Optional[str] = None,
        **kwargs,
    ) -> PostResult:
        """
        Upload a video to a Facebook Page.
        
        Facebook video upload uses a resumable upload protocol:
        1. Start upload session
        2. Upload video chunks
        3. Finish upload
        
        Args:
            access_token: User access token (will get page token)
            video_path: Path to video file
            title: Video title
            description: Video description
            page_id: Facebook Page ID (if not provided, uses first page)
            
        Returns:
            PostResult with upload status
        """
        try:
            # Get page access token
            profile = await self.get_user_profile(access_token)
            if not profile:
                return PostResult(success=False, error="Could not get Facebook profile")
            
            if profile.metadata.get("type") != "page":
                return PostResult(
                    success=False,
                    error="Video posting requires a Facebook Page",
                )
            
            page_access_token = profile.metadata.get("page_access_token")
            target_page_id = page_id or profile.platform_user_id
            
            if not page_access_token:
                return PostResult(
                    success=False,
                    error="No page access token available",
                )
            
            if not os.path.exists(video_path):
                return PostResult(success=False, error="Video file not found")
            
            file_size = os.path.getsize(video_path)
            
            # Step 1: Start upload session
            start_response = await self.client.post(
                f"{self.GRAPH_API}/{target_page_id}/videos",
                params={
                    "access_token": page_access_token,
                    "upload_phase": "start",
                    "file_size": file_size,
                },
            )
            
            if start_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Upload start failed: {start_response.text}",
                )
            
            start_data = start_response.json()
            upload_session_id = start_data.get("upload_session_id")
            video_id = start_data.get("video_id")
            
            if not upload_session_id:
                return PostResult(
                    success=False,
                    error="No upload session ID received",
                )
            
            # Step 2: Upload video (single chunk for simplicity)
            with open(video_path, "rb") as f:
                video_data = f.read()
            
            transfer_response = await self.client.post(
                f"{self.GRAPH_API}/{target_page_id}/videos",
                params={
                    "access_token": page_access_token,
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": 0,
                },
                files={"video_file_chunk": video_data},
                timeout=300.0,
            )
            
            if transfer_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Video transfer failed: {transfer_response.text}",
                )
            
            # Step 3: Finish upload
            finish_response = await self.client.post(
                f"{self.GRAPH_API}/{target_page_id}/videos",
                params={
                    "access_token": page_access_token,
                    "upload_phase": "finish",
                    "upload_session_id": upload_session_id,
                    "title": title[:100],
                    "description": description[:5000],
                },
            )
            
            if finish_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Upload finish failed: {finish_response.text}",
                )
            
            finish_data = finish_response.json()
            
            return PostResult(
                success=True,
                post_id=video_id,
                post_url=f"https://facebook.com/{video_id}",
                metadata={"success": finish_data.get("success")},
            )
            
        except Exception as e:
            logger.exception("Facebook upload error")
            return PostResult(success=False, error=str(e))
    
    # =========================================================================
    # Analytics Methods
    # =========================================================================
    
    async def get_video_analytics(
        self,
        access_token: str,
        video_id: str,
    ) -> Optional[AnalyticsData]:
        """Get analytics for a specific video."""
        try:
            # Get video insights
            response = await self.client.get(
                f"{self.GRAPH_API}/{video_id}",
                params={
                    "access_token": access_token,
                    "fields": "views,likes.summary(true),comments.summary(true),shares",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Facebook analytics fetch failed: {response.text}")
                return None
            
            data = response.json()
            
            views = data.get("views", 0)
            likes = data.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = data.get("shares", {}).get("count", 0)
            
            engagement_rate = ((likes + comments + shares) / views * 100) if views > 0 else 0
            
            return AnalyticsData(
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=round(engagement_rate, 2),
            )
            
        except Exception as e:
            logger.exception("Facebook analytics fetch error")
            return None
    
    async def get_account_analytics(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Get page-level analytics."""
        try:
            profile = await self.get_user_profile(access_token)
            if not profile or profile.metadata.get("type") != "page":
                return None
            
            page_id = profile.platform_user_id
            page_token = profile.metadata.get("page_access_token")
            
            response = await self.client.get(
                f"{self.GRAPH_API}/{page_id}/insights",
                params={
                    "access_token": page_token,
                    "metric": "page_impressions,page_engaged_users,page_video_views,page_fans",
                    "period": "day",
                    "since": int(start_date.timestamp()),
                    "until": int(end_date.timestamp()),
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Facebook page analytics failed: {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            logger.exception("Facebook page analytics error")
            return None

