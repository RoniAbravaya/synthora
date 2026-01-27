"""
Base Analytics Fetcher

Abstract base class for platform-specific analytics fetchers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class FetchResult:
    """
    Result from an analytics fetch operation.
    
    Attributes:
        success: Whether the fetch was successful
        error: Error message if failed
        views: Total view count
        likes: Total like count
        comments: Total comment count
        shares: Total share count
        saves: Total save/bookmark count
        watch_time_seconds: Total watch time in seconds
        avg_view_duration: Average view duration in seconds
        retention_rate: Average % of video watched
        reach: Unique accounts reached
        impressions: Total impressions
        click_through_rate: CTR percentage
        follower_change: Net follower change
        raw_data: Raw API response for debugging
    """
    success: bool = True
    error: Optional[str] = None
    
    # Primary metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    
    # Watch metrics
    watch_time_seconds: int = 0
    avg_view_duration: float = 0.0
    retention_rate: float = 0.0
    
    # Reach metrics
    reach: int = 0
    impressions: int = 0
    click_through_rate: float = 0.0
    
    # Growth metrics
    follower_change: int = 0
    
    # Raw data
    raw_data: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ChannelAnalytics:
    """
    Channel/account-level analytics.
    
    Attributes:
        subscribers: Total subscriber/follower count
        total_views: Total views across all videos
        total_videos: Total video count
        avg_views_per_video: Average views per video
        growth_rate: Subscriber growth rate
        raw_data: Raw API response
    """
    subscribers: int = 0
    total_views: int = 0
    total_videos: int = 0
    avg_views_per_video: float = 0.0
    growth_rate: float = 0.0
    raw_data: Optional[Dict[str, Any]] = field(default_factory=dict)


class BaseFetcher(ABC):
    """
    Abstract base class for analytics fetchers.
    
    Each platform should implement its own fetcher class
    that inherits from this base.
    """
    
    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize the fetcher.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token (for token refresh)
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    @abstractmethod
    async def fetch_video_analytics(
        self,
        video_id: str,
    ) -> FetchResult:
        """
        Fetch analytics for a specific video.
        
        Args:
            video_id: Platform-specific video/post ID
            
        Returns:
            FetchResult with video analytics
        """
        pass
    
    @abstractmethod
    async def fetch_channel_analytics(self) -> ChannelAnalytics:
        """
        Fetch channel/account-level analytics.
        
        Returns:
            ChannelAnalytics with account metrics
        """
        pass
    
    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            New access token, or None if refresh failed
        """
        # Default implementation does nothing
        # Subclasses can override if they support token refresh
        return None
