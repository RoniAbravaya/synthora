"""
Facebook Analytics Fetcher

Fetches analytics data from Facebook Graph API.
"""

import logging
from typing import Dict, Any, Optional

import httpx

from app.services.analytics_fetchers.base import BaseFetcher, FetchResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class FacebookAnalyticsFetcher(BaseFetcher):
    """
    Facebook analytics fetcher using Meta Graph API.
    
    Fetches video insights from Facebook Pages.
    Requires Page access token with pages_read_engagement permission.
    """
    
    API_BASE = "https://graph.facebook.com/v18.0"
    
    @property
    def platform_name(self) -> str:
        return "Facebook"
    
    async def fetch_video_analytics(self, video_id: str) -> FetchResult:
        """
        Fetch analytics for a Facebook video.
        
        Args:
            video_id: Facebook video ID
            
        Returns:
            FetchResult with video analytics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Fetch video insights
                response = await client.get(
                    f"{self.API_BASE}/{video_id}/video_insights",
                    params={
                        "metric": "total_video_views,total_video_views_unique,total_video_avg_time_watched,total_video_complete_views,total_video_10s_views",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                insights_data = {}
                if response.status_code == 200:
                    data = response.json()
                    for insight in data.get("data", []):
                        name = insight.get("name")
                        values = insight.get("values", [])
                        if values:
                            insights_data[name] = values[0].get("value", 0)
                
                # Fetch basic video info (likes, comments, shares)
                video_response = await client.get(
                    f"{self.API_BASE}/{video_id}",
                    params={
                        "fields": "id,title,description,likes.summary(true),comments.summary(true),shares",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if video_response.status_code != 200:
                    error_data = video_response.json()
                    return FetchResult(
                        success=False,
                        error=f"Facebook API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    )
                
                video_data = video_response.json()
                
                # Extract metrics
                likes = video_data.get("likes", {}).get("summary", {}).get("total_count", 0)
                comments = video_data.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares = video_data.get("shares", {}).get("count", 0)
                
                views = int(insights_data.get("total_video_views", 0))
                reach = int(insights_data.get("total_video_views_unique", 0))
                avg_watch_time = float(insights_data.get("total_video_avg_time_watched", 0))
                
                return FetchResult(
                    success=True,
                    views=views,
                    likes=int(likes),
                    comments=int(comments),
                    shares=int(shares),
                    reach=reach,
                    avg_view_duration=avg_watch_time,
                    raw_data={
                        "insights": insights_data,
                        "video": video_data,
                    },
                )
                
        except httpx.TimeoutException:
            return FetchResult(success=False, error="Request timed out")
        except Exception as e:
            self._log_error(f"Failed to fetch video analytics: {e}")
            return FetchResult(success=False, error=str(e))
    
    async def fetch_channel_analytics(self) -> Dict[str, Any]:
        """
        Fetch overall Facebook Page analytics.
        
        Returns:
            Dictionary with page-level metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get page info
                # First, get the user's pages
                pages_response = await client.get(
                    f"{self.API_BASE}/me/accounts",
                    params={
                        "fields": "id,name,fan_count,followers_count,access_token",
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )
                
                if pages_response.status_code != 200:
                    return {"error": "Failed to fetch pages"}
                
                pages_data = pages_response.json()
                pages = pages_data.get("data", [])
                
                if not pages:
                    return {"error": "No pages found"}
                
                # Use the first page (or you could let user select)
                page = pages[0]
                page_id = page.get("id")
                page_token = page.get("access_token")
                
                # Get page insights
                insights = {}
                try:
                    insights_response = await client.get(
                        f"{self.API_BASE}/{page_id}/insights",
                        params={
                            "metric": "page_impressions,page_engaged_users,page_post_engagements,page_video_views",
                            "period": "day",
                            "access_token": page_token,
                        },
                        timeout=30.0,
                    )
                    
                    if insights_response.status_code == 200:
                        insights_data = insights_response.json()
                        for insight in insights_data.get("data", []):
                            name = insight.get("name")
                            values = insight.get("values", [])
                            if values:
                                insights[name] = values[-1].get("value", 0)
                except Exception:
                    pass  # Insights might fail
                
                return {
                    "page_id": page_id,
                    "page_name": page.get("name"),
                    "fans": int(page.get("fan_count", 0)),
                    "followers": int(page.get("followers_count", 0)),
                    "daily_impressions": insights.get("page_impressions", 0),
                    "daily_engaged_users": insights.get("page_engaged_users", 0),
                    "daily_post_engagements": insights.get("page_post_engagements", 0),
                    "daily_video_views": insights.get("page_video_views", 0),
                }
                
        except Exception as e:
            self._log_error(f"Failed to fetch page analytics: {e}")
            return {"error": str(e)}
    
    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh Facebook (Meta) access token.
        
        Note: Page tokens derived from long-lived user tokens don't expire.
        """
        if not self.access_token:
            return None
        
        try:
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

