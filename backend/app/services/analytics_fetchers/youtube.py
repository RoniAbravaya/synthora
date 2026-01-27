"""
YouTube Analytics Fetcher

Fetches analytics data from the YouTube Analytics API.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

import httpx

from .base import BaseFetcher, FetchResult, ChannelAnalytics

logger = logging.getLogger(__name__)

# YouTube API endpoints
YOUTUBE_DATA_API = "https://www.googleapis.com/youtube/v3"
YOUTUBE_ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2"


class YouTubeFetcher(BaseFetcher):
    """
    Fetcher for YouTube video and channel analytics.
    
    Uses both the YouTube Data API (for basic video info) and
    YouTube Analytics API (for detailed metrics).
    
    Required OAuth scopes:
    - https://www.googleapis.com/auth/youtube.readonly
    - https://www.googleapis.com/auth/yt-analytics.readonly
    """
    
    async def fetch_video_analytics(
        self,
        video_id: str,
    ) -> FetchResult:
        """
        Fetch analytics for a YouTube video.
        
        Args:
            video_id: YouTube video ID (the part after watch?v=)
            
        Returns:
            FetchResult with video metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # First, get basic video statistics from Data API
                video_stats = await self._fetch_video_stats(client, video_id)
                
                if not video_stats:
                    return FetchResult(
                        success=False,
                        error="Failed to fetch video statistics",
                    )
                
                # Try to get detailed analytics from Analytics API
                # Note: Analytics API requires channel ownership
                detailed_analytics = await self._fetch_detailed_analytics(
                    client, video_id
                )
                
                # Combine results
                # Note: impressions and click_through_rate require YouTube Partner 
                # Program access, so they default to 0 for non-partner channels
                return FetchResult(
                    success=True,
                    views=video_stats.get("viewCount", 0),
                    likes=video_stats.get("likeCount", 0),
                    comments=video_stats.get("commentCount", 0),
                    shares=detailed_analytics.get("shares", 0),
                    saves=0,  # YouTube doesn't have saves
                    watch_time_seconds=detailed_analytics.get("estimatedMinutesWatched", 0) * 60,
                    avg_view_duration=detailed_analytics.get("averageViewDuration", 0),
                    retention_rate=detailed_analytics.get("averageViewPercentage", 0),
                    impressions=0,  # Requires YouTube Partner Program access
                    click_through_rate=0,  # Requires YouTube Partner Program access
                    follower_change=detailed_analytics.get("subscribersGained", 0) - 
                                   detailed_analytics.get("subscribersLost", 0),
                    raw_data={
                        "video_stats": video_stats,
                        "detailed_analytics": detailed_analytics,
                    },
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch YouTube analytics for {video_id}: {e}")
            return FetchResult(
                success=False,
                error=str(e),
            )
    
    async def _fetch_video_stats(
        self,
        client: httpx.AsyncClient,
        video_id: str,
    ) -> Optional[Dict[str, int]]:
        """
        Fetch basic video statistics from YouTube Data API.
        
        Args:
            client: HTTP client
            video_id: YouTube video ID
            
        Returns:
            Dictionary with view/like/comment counts
        """
        try:
            response = await client.get(
                f"{YOUTUBE_DATA_API}/videos",
                params={
                    "part": "statistics,contentDetails",
                    "id": video_id,
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube Data API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                logger.warning(f"No video found with ID: {video_id}")
                return None
            
            stats = items[0].get("statistics", {})
            content = items[0].get("contentDetails", {})
            
            return {
                "viewCount": int(stats.get("viewCount", 0)),
                "likeCount": int(stats.get("likeCount", 0)),
                "commentCount": int(stats.get("commentCount", 0)),
                "favoriteCount": int(stats.get("favoriteCount", 0)),
                "duration": content.get("duration", "PT0S"),
            }
            
        except Exception as e:
            logger.error(f"Error fetching video stats: {e}")
            return None
    
    async def _fetch_detailed_analytics(
        self,
        client: httpx.AsyncClient,
        video_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch detailed analytics from YouTube Analytics API.
        
        Note: This requires the video to be on a channel the user owns.
        
        Args:
            client: HTTP client
            video_id: YouTube video ID
            
        Returns:
            Dictionary with detailed metrics
        """
        try:
            # Calculate date range (last 28 days)
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=28)
            
            # Note: 'impressions' and 'impressionClickThroughRate' require YouTube 
            # Partner Program membership or elevated API access, so we exclude them
            # to avoid 400 errors for non-partner channels.
            response = await client.get(
                f"{YOUTUBE_ANALYTICS_API}/reports",
                params={
                    "ids": "channel==MINE",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "metrics": ",".join([
                        "views",
                        "estimatedMinutesWatched",
                        "averageViewDuration",
                        "averageViewPercentage",
                        "likes",
                        "dislikes",
                        "shares",
                        "comments",
                        "subscribersGained",
                        "subscribersLost",
                    ]),
                    "filters": f"video=={video_id}",
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
            
            if response.status_code != 200:
                # Analytics API might not be available or video not owned
                logger.warning(
                    f"YouTube Analytics API returned {response.status_code}: {response.text}"
                )
                return {}
            
            data = response.json()
            rows = data.get("rows", [])
            
            if not rows:
                return {}
            
            # Map column headers to values
            headers = [h.get("name") for h in data.get("columnHeaders", [])]
            values = rows[0] if rows else []
            
            result = {}
            for header, value in zip(headers, values):
                result[header] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching detailed analytics: {e}")
            return {}
    
    async def fetch_channel_analytics(self) -> ChannelAnalytics:
        """
        Fetch channel-level analytics.
        
        Returns:
            ChannelAnalytics with channel metrics
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get channel info from Data API
                response = await client.get(
                    f"{YOUTUBE_DATA_API}/channels",
                    params={
                        "part": "statistics,snippet",
                        "mine": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch channel info: {response.status_code}")
                    return ChannelAnalytics()
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    return ChannelAnalytics()
                
                channel = items[0]
                stats = channel.get("statistics", {})
                
                subscribers = int(stats.get("subscriberCount", 0))
                total_views = int(stats.get("viewCount", 0))
                total_videos = int(stats.get("videoCount", 0))
                
                avg_views = total_views / total_videos if total_videos > 0 else 0
                
                # Get channel analytics for growth rate
                growth_data = await self._fetch_channel_growth(client)
                
                return ChannelAnalytics(
                    subscribers=subscribers,
                    total_views=total_views,
                    total_videos=total_videos,
                    avg_views_per_video=avg_views,
                    growth_rate=growth_data.get("growth_rate", 0),
                    raw_data={
                        "channel": channel,
                        "growth": growth_data,
                    },
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch channel analytics: {e}")
            return ChannelAnalytics()
    
    async def _fetch_channel_growth(
        self,
        client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        """
        Fetch channel growth metrics from Analytics API.
        
        Args:
            client: HTTP client
            
        Returns:
            Dictionary with growth metrics
        """
        try:
            # Last 28 days vs previous 28 days
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=28)
            
            response = await client.get(
                f"{YOUTUBE_ANALYTICS_API}/reports",
                params={
                    "ids": "channel==MINE",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "metrics": "subscribersGained,subscribersLost,views",
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
            
            if response.status_code != 200:
                return {}
            
            data = response.json()
            rows = data.get("rows", [])
            
            if not rows:
                return {}
            
            headers = [h.get("name") for h in data.get("columnHeaders", [])]
            values = rows[0]
            
            result = dict(zip(headers, values))
            
            # Calculate net growth
            gained = result.get("subscribersGained", 0)
            lost = result.get("subscribersLost", 0)
            result["net_growth"] = gained - lost
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching channel growth: {e}")
            return {}
