"""
Instagram Integration

OAuth and API client for Instagram (via Meta Graph API).
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


class InstagramClient(BaseSocialClient):
    """
    Instagram OAuth and API client.
    
    Uses Meta's Graph API for Instagram Business/Creator accounts.
    Note: Only Business and Creator accounts can use the API.
    """
    
    # OAuth endpoints (Meta)
    AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    # API endpoints
    GRAPH_API = "https://graph.facebook.com/v18.0"
    
    # Required scopes for Instagram
    DEFAULT_SCOPES = [
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_insights",
        "pages_show_list",
        "pages_read_engagement",
    ]
    
    def __init__(self):
        """Initialize the Instagram client."""
        super().__init__()
        settings = get_settings()
        
        self.default_config = OAuthConfig(
            client_id=settings.META_APP_ID or "",
            client_secret=settings.META_APP_SECRET or "",
            redirect_uri=settings.instagram_redirect_uri,
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
        """Get the Meta OAuth authorization URL for Instagram."""
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
                logger.error(f"Instagram token exchange failed: {response.text}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"Instagram token error: {data}")
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
                # Fall back to short-lived token
                return {
                    "access_token": short_lived_token,
                    "expires_in": data.get("expires_in", 3600),
                }
            
            long_data = long_lived_response.json()
            
            return {
                "access_token": long_data.get("access_token", short_lived_token),
                "expires_in": long_data.get("expires_in", 5184000),  # ~60 days
                "token_type": "Bearer",
            }
            
        except Exception as e:
            logger.exception("Instagram token exchange error")
            return None
    
    async def refresh_access_token(
        self,
        config: Optional[OAuthConfig] = None,
        refresh_token: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token.
        
        Note: Instagram/Meta long-lived tokens can be refreshed
        before they expire (within 60 days).
        """
        config = config or self.default_config
        
        try:
            response = await self.client.get(
                f"{self.GRAPH_API}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "fb_exchange_token": refresh_token,  # Use current token
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Instagram token refresh failed: {response.text}")
                return None
            
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_in": data.get("expires_in", 5184000),
            }
            
        except Exception as e:
            logger.exception("Instagram token refresh error")
            return None
    
    # =========================================================================
    # Profile Methods
    # =========================================================================
    
    async def get_user_profile(
        self,
        access_token: str,
    ) -> Optional[UserProfile]:
        """Get the authenticated user's Instagram profile."""
        try:
            # First, get the Facebook Page connected to Instagram
            pages_response = await self.client.get(
                f"{self.GRAPH_API}/me/accounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,instagram_business_account",
                },
            )
            
            if pages_response.status_code != 200:
                logger.error(f"Instagram pages fetch failed: {pages_response.text}")
                return None
            
            pages_data = pages_response.json()
            pages = pages_data.get("data", [])
            
            # Find page with Instagram account
            instagram_account_id = None
            for page in pages:
                ig_account = page.get("instagram_business_account", {})
                if ig_account.get("id"):
                    instagram_account_id = ig_account["id"]
                    break
            
            if not instagram_account_id:
                logger.warning("No Instagram Business account found")
                return None
            
            # Get Instagram account details
            ig_response = await self.client.get(
                f"{self.GRAPH_API}/{instagram_account_id}",
                params={
                    "access_token": access_token,
                    "fields": "id,username,name,profile_picture_url,followers_count,follows_count,media_count",
                },
            )
            
            if ig_response.status_code != 200:
                logger.error(f"Instagram profile fetch failed: {ig_response.text}")
                return None
            
            data = ig_response.json()
            
            return UserProfile(
                platform_user_id=data["id"],
                username=data.get("username", ""),
                display_name=data.get("name"),
                profile_url=f"https://instagram.com/{data.get('username', '')}",
                avatar_url=data.get("profile_picture_url"),
                followers_count=data.get("followers_count", 0),
                metadata={
                    "follows_count": data.get("follows_count", 0),
                    "media_count": data.get("media_count", 0),
                },
            )
            
        except Exception as e:
            logger.exception("Instagram profile fetch error")
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
        **kwargs,
    ) -> PostResult:
        """
        Upload a video to Instagram (Reels).
        
        Instagram video upload is a multi-step process:
        1. Create a media container
        2. Wait for processing
        3. Publish the media
        
        Args:
            access_token: OAuth access token
            video_path: Path to video file (or URL)
            title: Not used for Instagram
            description: Caption for the post
            
        Returns:
            PostResult with upload status
        """
        try:
            # Get Instagram account ID
            profile = await self.get_user_profile(access_token)
            if not profile:
                return PostResult(success=False, error="Could not get Instagram account")
            
            ig_account_id = profile.platform_user_id
            
            # For Instagram, we need a publicly accessible URL
            # In production, upload to GCS first and use that URL
            video_url = kwargs.get("video_url", video_path)
            
            if not video_url.startswith("http"):
                return PostResult(
                    success=False,
                    error="Instagram requires a public video URL",
                )
            
            # Step 1: Create media container
            container_response = await self.client.post(
                f"{self.GRAPH_API}/{ig_account_id}/media",
                params={
                    "access_token": access_token,
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": description[:2200],  # Instagram limit
                },
            )
            
            if container_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Container creation failed: {container_response.text}",
                )
            
            container_data = container_response.json()
            container_id = container_data.get("id")
            
            if not container_id:
                return PostResult(
                    success=False,
                    error="No container ID received",
                )
            
            # Step 2: Check container status (Instagram processes the video)
            # In production, poll this endpoint until status is "FINISHED"
            
            # Step 3: Publish the media
            publish_response = await self.client.post(
                f"{self.GRAPH_API}/{ig_account_id}/media_publish",
                params={
                    "access_token": access_token,
                    "creation_id": container_id,
                },
            )
            
            if publish_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Publish failed: {publish_response.text}",
                )
            
            publish_data = publish_response.json()
            media_id = publish_data.get("id")
            
            return PostResult(
                success=True,
                post_id=media_id,
                post_url=f"https://instagram.com/reel/{media_id}",
                metadata={"container_id": container_id},
            )
            
        except Exception as e:
            logger.exception("Instagram upload error")
            return PostResult(success=False, error=str(e))
    
    # =========================================================================
    # Analytics Methods
    # =========================================================================
    
    async def get_video_analytics(
        self,
        access_token: str,
        video_id: str,
    ) -> Optional[AnalyticsData]:
        """Get analytics for a specific video/reel."""
        try:
            response = await self.client.get(
                f"{self.GRAPH_API}/{video_id}/insights",
                params={
                    "access_token": access_token,
                    "metric": "plays,reach,likes,comments,shares,saved",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Instagram analytics fetch failed: {response.text}")
                return None
            
            data = response.json()
            insights = {
                item["name"]: item["values"][0]["value"]
                for item in data.get("data", [])
            }
            
            views = insights.get("plays", 0)
            likes = insights.get("likes", 0)
            comments = insights.get("comments", 0)
            shares = insights.get("shares", 0)
            saves = insights.get("saved", 0)
            reach = insights.get("reach", 0)
            
            engagement_rate = ((likes + comments + shares + saves) / reach * 100) if reach > 0 else 0
            
            return AnalyticsData(
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                reach=reach,
                engagement_rate=round(engagement_rate, 2),
            )
            
        except Exception as e:
            logger.exception("Instagram analytics fetch error")
            return None
    
    async def get_account_analytics(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Get account-level analytics."""
        try:
            profile = await self.get_user_profile(access_token)
            if not profile:
                return None
            
            ig_account_id = profile.platform_user_id
            
            response = await self.client.get(
                f"{self.GRAPH_API}/{ig_account_id}/insights",
                params={
                    "access_token": access_token,
                    "metric": "impressions,reach,follower_count,profile_views",
                    "period": "day",
                    "since": int(start_date.timestamp()),
                    "until": int(end_date.timestamp()),
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Instagram account analytics failed: {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            logger.exception("Instagram account analytics error")
            return None

