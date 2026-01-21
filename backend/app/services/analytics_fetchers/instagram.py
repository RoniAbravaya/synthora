"""
Instagram Analytics Fetcher

Fetches analytics data from Instagram Graph API.
"""

import logging
from typing import Dict, Any, Optional

import httpx

from app.services.analytics_fetchers.base import BaseFetcher, FetchResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InstagramAnalyticsFetcher(BaseFetcher):
    """
    Instagram analytics fetcher using Meta Graph API.
    
    Requires Instagram Business or Creator account connected to a Facebook Page.
    Uses Instagram Graph API for media insights.
    """
    
    API_BASE = "https://graph.facebook.com/v18.0"
    
    @property
    def platform_name(self) -> str:
        return "Instagram"
    
    async def fetch_video_analytics(self, video_id: str) -> FetchResult:
        """
        Fetch analytics for an Instagram video (Reel).
        
        Args:
            video_id: Instagram media ID
            
        Returns:
            FetchResult with video analytics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Fetch media insights
                # Available metrics for Reels: plays, reach, saved, shares, comments, likes
                response = await client.get(
                    f"{self.API_BASE}/{video_id}/insights",
                    params={
                        "metric": "plays,reach,saved,shares,comments,likes,total_interactions",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    
                    # Try fetching basic media info if insights fail
                    return await self._fetch_basic_media_info(video_id)
                
                data = response.json()
                insights = data.get("data", [])
                
                # Parse insights into metrics
                metrics = {}
                for insight in insights:
                    name = insight.get("name")
                    values = insight.get("values", [])
                    if values:
                        metrics[name] = values[0].get("value", 0)
                
                return FetchResult(
                    success=True,
                    views=int(metrics.get("plays", 0)),
                    likes=int(metrics.get("likes", 0)),
                    comments=int(metrics.get("comments", 0)),
                    shares=int(metrics.get("shares", 0)),
                    saves=int(metrics.get("saved", 0)),
                    reach=int(metrics.get("reach", 0)),
                    raw_data=data,
                )
                
        except httpx.TimeoutException:
            return FetchResult(success=False, error="Request timed out")
        except Exception as e:
            self._log_error(f"Failed to fetch video analytics: {e}")
            return FetchResult(success=False, error=str(e))
    
    async def _fetch_basic_media_info(self, media_id: str) -> FetchResult:
        """
        Fetch basic media info when insights are not available.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            FetchResult with basic metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{media_id}",
                    params={
                        "fields": "id,like_count,comments_count,media_type,timestamp",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    return FetchResult(
                        success=False,
                        error=f"Instagram API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    )
                
                data = response.json()
                
                return FetchResult(
                    success=True,
                    likes=int(data.get("like_count", 0)),
                    comments=int(data.get("comments_count", 0)),
                    raw_data=data,
                )
                
        except Exception as e:
            return FetchResult(success=False, error=str(e))
    
    async def fetch_channel_analytics(self) -> Dict[str, Any]:
        """
        Fetch overall Instagram account analytics.
        
        Returns:
            Dictionary with account-level metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # First, get the Instagram Business Account ID
                # This requires the user's Facebook Page access token
                
                # Get user's Instagram account info
                response = await client.get(
                    f"{self.API_BASE}/me",
                    params={
                        "fields": "id,username,name,followers_count,follows_count,media_count,profile_picture_url",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    return {"error": "Failed to fetch account data"}
                
                data = response.json()
                
                # Try to get account insights
                insights = {}
                try:
                    insights_response = await client.get(
                        f"{self.API_BASE}/{data.get('id')}/insights",
                        params={
                            "metric": "impressions,reach,profile_views",
                            "period": "day",
                            "access_token": self.access_token,
                        },
                        timeout=30.0,
                    )
                    
                    if insights_response.status_code == 200:
                        insights_data = insights_response.json()
                        for insight in insights_data.get("data", []):
                            name = insight.get("name")
                            values = insight.get("values", [])
                            if values:
                                insights[name] = values[0].get("value", 0)
                except Exception:
                    pass  # Insights might not be available
                
                return {
                    "account_id": data.get("id"),
                    "username": data.get("username"),
                    "name": data.get("name"),
                    "followers": int(data.get("followers_count", 0)),
                    "following": int(data.get("follows_count", 0)),
                    "media_count": int(data.get("media_count", 0)),
                    "daily_impressions": insights.get("impressions", 0),
                    "daily_reach": insights.get("reach", 0),
                    "daily_profile_views": insights.get("profile_views", 0),
                }
                
        except Exception as e:
            self._log_error(f"Failed to fetch account analytics: {e}")
            return {"error": str(e)}
    
    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh Instagram (Meta) access token.
        
        Note: Long-lived tokens need to be refreshed before they expire.
        """
        if not self.access_token:
            return None
        
        try:
            settings = get_settings()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "fb_exchange_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    return self.access_token
                    
        except Exception as e:
            self._log_error(f"Failed to refresh token: {e}")
        
        return None

