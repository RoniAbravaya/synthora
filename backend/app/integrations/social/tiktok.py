"""
TikTok Integration

OAuth and API client for TikTok.
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


class TikTokClient(BaseSocialClient):
    """
    TikTok OAuth and API client.
    
    Uses TikTok's OAuth 2.0 for authentication and the Content Posting API
    for video uploads.
    """
    
    # OAuth endpoints
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    
    # API endpoints
    API_BASE = "https://open.tiktokapis.com/v2"
    
    # Required scopes
    DEFAULT_SCOPES = [
        "user.info.basic",
        "video.publish",
        "video.upload",
    ]
    
    def __init__(self):
        """Initialize the TikTok client."""
        super().__init__()
        settings = get_settings()
        
        self.default_config = OAuthConfig(
            client_id=settings.TIKTOK_CLIENT_KEY or "",
            client_secret=settings.TIKTOK_CLIENT_SECRET or "",
            redirect_uri=settings.tiktok_redirect_uri,
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
        """Get the TikTok OAuth authorization URL."""
        config = config or self.default_config
        
        params = {
            "client_key": config.client_id,
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
            response = await self.client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config.redirect_uri,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"TikTok token exchange failed: {response.text}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"TikTok token error: {data}")
                return None
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 86400),
                "open_id": data.get("open_id"),
                "scope": data.get("scope", ""),
            }
            
        except Exception as e:
            logger.exception("TikTok token exchange error")
            return None
    
    async def refresh_access_token(
        self,
        config: Optional[OAuthConfig] = None,
        refresh_token: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        config = config or self.default_config
        
        try:
            response = await self.client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": config.client_id,
                    "client_secret": config.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"TikTok token refresh failed: {response.text}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"TikTok refresh error: {data}")
                return None
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 86400),
            }
            
        except Exception as e:
            logger.exception("TikTok token refresh error")
            return None
    
    # =========================================================================
    # Profile Methods
    # =========================================================================
    
    async def get_user_profile(
        self,
        access_token: str,
    ) -> Optional[UserProfile]:
        """Get the authenticated user's TikTok profile."""
        try:
            response = await self.client.get(
                f"{self.API_BASE}/user/info/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "fields": "open_id,union_id,avatar_url,display_name,username,follower_count,following_count,likes_count,video_count",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"TikTok profile fetch failed: {response.text}")
                return None
            
            data = response.json()
            
            if data.get("error", {}).get("code") != "ok":
                logger.error(f"TikTok profile error: {data}")
                return None
            
            user_data = data.get("data", {}).get("user", {})
            
            return UserProfile(
                platform_user_id=user_data.get("open_id", ""),
                username=user_data.get("username", ""),
                display_name=user_data.get("display_name"),
                profile_url=f"https://tiktok.com/@{user_data.get('username', '')}",
                avatar_url=user_data.get("avatar_url"),
                followers_count=user_data.get("follower_count", 0),
                metadata={
                    "following_count": user_data.get("following_count", 0),
                    "likes_count": user_data.get("likes_count", 0),
                    "video_count": user_data.get("video_count", 0),
                },
            )
            
        except Exception as e:
            logger.exception("TikTok profile fetch error")
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
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
        **kwargs,
    ) -> PostResult:
        """
        Upload a video to TikTok.
        
        Uses the Content Posting API which requires:
        1. Initialize upload
        2. Upload video chunks
        3. Publish video
        
        Args:
            access_token: OAuth access token
            video_path: Path to video file
            title: Video title (used in description)
            description: Video description/caption
            privacy_level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY
            disable_duet: Disable duet feature
            disable_comment: Disable comments
            disable_stitch: Disable stitch feature
            
        Returns:
            PostResult with upload status
        """
        try:
            if not os.path.exists(video_path):
                return PostResult(success=False, error="Video file not found")
            
            file_size = os.path.getsize(video_path)
            
            # Step 1: Initialize upload
            init_response = await self.client.post(
                f"{self.API_BASE}/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": f"{title}\n\n{description}"[:2200],  # TikTok limit
                        "privacy_level": privacy_level,
                        "disable_duet": disable_duet,
                        "disable_comment": disable_comment,
                        "disable_stitch": disable_stitch,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": file_size,  # Single chunk for simplicity
                        "total_chunk_count": 1,
                    },
                },
            )
            
            if init_response.status_code != 200:
                return PostResult(
                    success=False,
                    error=f"Upload init failed: {init_response.text}",
                )
            
            init_data = init_response.json()
            
            if init_data.get("error", {}).get("code") != "ok":
                return PostResult(
                    success=False,
                    error=f"Upload init error: {init_data}",
                )
            
            upload_url = init_data.get("data", {}).get("upload_url")
            publish_id = init_data.get("data", {}).get("publish_id")
            
            if not upload_url:
                return PostResult(
                    success=False,
                    error="No upload URL received",
                )
            
            # Step 2: Upload video
            with open(video_path, "rb") as f:
                video_data = f.read()
            
            upload_response = await self.client.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                },
                content=video_data,
                timeout=300.0,
            )
            
            if upload_response.status_code not in [200, 201]:
                return PostResult(
                    success=False,
                    error=f"Video upload failed: {upload_response.text}",
                )
            
            # Step 3: Check publish status
            # TikTok processes videos asynchronously, so we return the publish_id
            return PostResult(
                success=True,
                post_id=publish_id,
                metadata={
                    "status": "processing",
                    "message": "Video uploaded, processing by TikTok",
                },
            )
            
        except Exception as e:
            logger.exception("TikTok upload error")
            return PostResult(success=False, error=str(e))
    
    async def check_publish_status(
        self,
        access_token: str,
        publish_id: str,
    ) -> Dict[str, Any]:
        """Check the status of a video publish."""
        try:
            response = await self.client.post(
                f"{self.API_BASE}/post/publish/status/fetch/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"publish_id": publish_id},
            )
            
            if response.status_code != 200:
                return {"status": "error", "error": response.text}
            
            return response.json()
            
        except Exception as e:
            logger.exception("TikTok status check error")
            return {"status": "error", "error": str(e)}
    
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
            response = await self.client.post(
                f"{self.API_BASE}/video/query/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "filters": {
                        "video_ids": [video_id],
                    },
                    "fields": ["id", "title", "view_count", "like_count", "comment_count", "share_count"],
                },
            )
            
            if response.status_code != 200:
                logger.error(f"TikTok analytics fetch failed: {response.text}")
                return None
            
            data = response.json()
            videos = data.get("data", {}).get("videos", [])
            
            if not videos:
                return None
            
            video = videos[0]
            views = video.get("view_count", 0)
            likes = video.get("like_count", 0)
            comments = video.get("comment_count", 0)
            shares = video.get("share_count", 0)
            
            engagement_rate = ((likes + comments + shares) / views * 100) if views > 0 else 0
            
            return AnalyticsData(
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=round(engagement_rate, 2),
            )
            
        except Exception as e:
            logger.exception("TikTok analytics fetch error")
            return None
    
    async def get_account_analytics(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Get account-level analytics."""
        # TikTok's analytics API is limited
        # This would require additional scopes and may not be available
        # to all developers
        logger.info("TikTok account analytics not fully implemented")
        return None

