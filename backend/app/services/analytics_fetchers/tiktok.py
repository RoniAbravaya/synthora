"""
TikTok Analytics Fetcher

Fetches analytics data from TikTok Content Posting API.
"""

import logging
from typing import Dict, Any, Optional

import httpx

from app.services.analytics_fetchers.base import BaseFetcher, FetchResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TikTokAnalyticsFetcher(BaseFetcher):
    """
    TikTok analytics fetcher using TikTok Content Posting API.
    
    Note: TikTok's API has limited analytics access for most developers.
    Full analytics require TikTok Creator/Business API access.
    """
    
    API_BASE = "https://open.tiktokapis.com/v2"
    
    @property
    def platform_name(self) -> str:
        return "TikTok"
    
    async def fetch_video_analytics(self, video_id: str) -> FetchResult:
        """
        Fetch analytics for a TikTok video.
        
        Args:
            video_id: TikTok video ID
            
        Returns:
            FetchResult with video analytics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Query video info
                # Note: Requires video.list scope
                response = await client.post(
                    f"{self.API_BASE}/video/query/",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "filters": {
                            "video_ids": [video_id],
                        },
                        "fields": [
                            "id",
                            "title",
                            "view_count",
                            "like_count",
                            "comment_count",
                            "share_count",
                            "duration",
                        ],
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    return FetchResult(
                        success=False,
                        error=f"TikTok API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    )
                
                data = response.json()
                
                if data.get("error", {}).get("code") != "ok":
                    return FetchResult(
                        success=False,
                        error=f"TikTok API error: {data.get('error', {}).get('message', 'Unknown error')}",
                    )
                
                videos = data.get("data", {}).get("videos", [])
                
                if not videos:
                    return FetchResult(
                        success=False,
                        error=f"Video not found: {video_id}",
                    )
                
                video = videos[0]
                
                return FetchResult(
                    success=True,
                    views=int(video.get("view_count", 0)),
                    likes=int(video.get("like_count", 0)),
                    comments=int(video.get("comment_count", 0)),
                    shares=int(video.get("share_count", 0)),
                    raw_data=data,
                )
                
        except httpx.TimeoutException:
            return FetchResult(success=False, error="Request timed out")
        except Exception as e:
            self._log_error(f"Failed to fetch video analytics: {e}")
            return FetchResult(success=False, error=str(e))
    
    async def fetch_channel_analytics(self) -> Dict[str, Any]:
        """
        Fetch overall TikTok account analytics.
        
        Returns:
            Dictionary with account-level metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get user info
                response = await client.get(
                    f"{self.API_BASE}/user/info/",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    params={
                        "fields": "open_id,union_id,avatar_url,display_name,follower_count,following_count,likes_count,video_count",
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    return {"error": "Failed to fetch user data"}
                
                data = response.json()
                
                if data.get("error", {}).get("code") != "ok":
                    return {"error": data.get("error", {}).get("message", "Unknown error")}
                
                user = data.get("data", {}).get("user", {})
                
                return {
                    "user_id": user.get("open_id"),
                    "display_name": user.get("display_name"),
                    "followers": int(user.get("follower_count", 0)),
                    "following": int(user.get("following_count", 0)),
                    "total_likes": int(user.get("likes_count", 0)),
                    "video_count": int(user.get("video_count", 0)),
                }
                
        except Exception as e:
            self._log_error(f"Failed to fetch account analytics: {e}")
            return {"error": str(e)}
    
    async def refresh_access_token(self) -> Optional[str]:
        """Refresh TikTok OAuth token."""
        if not self.refresh_token:
            return None
        
        try:
            settings = get_settings()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE}/oauth/token/",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "client_key": settings.TIKTOK_CLIENT_KEY,
                        "client_secret": settings.TIKTOK_CLIENT_SECRET,
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data", {}).get("access_token"):
                        self.access_token = data["data"]["access_token"]
                        return self.access_token
                    
        except Exception as e:
            self._log_error(f"Failed to refresh token: {e}")
        
        return None

