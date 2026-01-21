"""
YouTube Analytics Fetcher

Fetches analytics data from YouTube Data API and Analytics API.
"""

import logging
from typing import Dict, Any, Optional

import httpx

from app.services.analytics_fetchers.base import BaseFetcher, FetchResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class YouTubeAnalyticsFetcher(BaseFetcher):
    """
    YouTube analytics fetcher using YouTube Data API v3 and YouTube Analytics API.
    
    Uses:
    - YouTube Data API v3 for video statistics
    - YouTube Analytics API for detailed metrics (watch time, etc.)
    """
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"
    
    @property
    def platform_name(self) -> str:
        return "YouTube"
    
    async def fetch_video_analytics(self, video_id: str) -> FetchResult:
        """
        Fetch analytics for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            FetchResult with video analytics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Fetch basic statistics from Data API
                stats_response = await client.get(
                    f"{self.API_BASE}/videos",
                    params={
                        "part": "statistics,contentDetails",
                        "id": video_id,
                    },
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=30.0,
                )
                
                if stats_response.status_code != 200:
                    error_data = stats_response.json()
                    return FetchResult(
                        success=False,
                        error=f"YouTube API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    )
                
                stats_data = stats_response.json()
                
                if not stats_data.get("items"):
                    return FetchResult(
                        success=False,
                        error=f"Video not found: {video_id}",
                    )
                
                video_stats = stats_data["items"][0]["statistics"]
                
                # Extract basic metrics
                views = int(video_stats.get("viewCount", 0))
                likes = int(video_stats.get("likeCount", 0))
                comments = int(video_stats.get("commentCount", 0))
                
                # YouTube doesn't expose shares directly via API
                # We'll try to get it from Analytics API
                shares = 0
                watch_time_seconds = 0
                avg_view_duration = 0.0
                
                # Try to fetch detailed analytics (requires YouTube Analytics API access)
                try:
                    analytics_response = await client.get(
                        f"{self.ANALYTICS_BASE}/reports",
                        params={
                            "ids": "channel==MINE",
                            "filters": f"video=={video_id}",
                            "metrics": "estimatedMinutesWatched,averageViewDuration,shares",
                            "startDate": "2020-01-01",
                            "endDate": "2099-12-31",
                        },
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        timeout=30.0,
                    )
                    
                    if analytics_response.status_code == 200:
                        analytics_data = analytics_response.json()
                        if analytics_data.get("rows"):
                            row = analytics_data["rows"][0]
                            watch_time_seconds = int(float(row[0]) * 60)  # Convert minutes to seconds
                            avg_view_duration = float(row[1])
                            shares = int(row[2]) if len(row) > 2 else 0
                except Exception as e:
                    # Analytics API might not be available, continue with basic stats
                    self._log_info(f"Could not fetch detailed analytics: {e}")
                
                return FetchResult(
                    success=True,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    watch_time_seconds=watch_time_seconds,
                    avg_view_duration=avg_view_duration,
                    raw_data=stats_data,
                )
                
        except httpx.TimeoutException:
            return FetchResult(success=False, error="Request timed out")
        except Exception as e:
            self._log_error(f"Failed to fetch video analytics: {e}")
            return FetchResult(success=False, error=str(e))
    
    async def fetch_channel_analytics(self) -> Dict[str, Any]:
        """
        Fetch overall channel analytics.
        
        Returns:
            Dictionary with channel-level metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get channel info
                channel_response = await client.get(
                    f"{self.API_BASE}/channels",
                    params={
                        "part": "statistics,snippet",
                        "mine": "true",
                    },
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=30.0,
                )
                
                if channel_response.status_code != 200:
                    return {"error": "Failed to fetch channel data"}
                
                channel_data = channel_response.json()
                
                if not channel_data.get("items"):
                    return {"error": "No channel found"}
                
                channel = channel_data["items"][0]
                stats = channel.get("statistics", {})
                snippet = channel.get("snippet", {})
                
                return {
                    "channel_id": channel.get("id"),
                    "channel_name": snippet.get("title"),
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                }
                
        except Exception as e:
            self._log_error(f"Failed to fetch channel analytics: {e}")
            return {"error": str(e)}
    
    async def refresh_access_token(self) -> Optional[str]:
        """Refresh YouTube OAuth token."""
        if not self.refresh_token:
            return None
        
        try:
            settings = get_settings()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.YOUTUBE_CLIENT_ID,
                        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    return self.access_token
                    
        except Exception as e:
            self._log_error(f"Failed to refresh token: {e}")
        
        return None

