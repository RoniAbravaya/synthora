"""
Base Analytics Fetcher

Abstract base class for platform-specific analytics fetchers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """
    Result of an analytics fetch operation.
    
    Attributes:
        success: Whether the fetch was successful
        views: View count
        likes: Like count
        comments: Comment count
        shares: Share count
        saves: Save/bookmark count
        watch_time_seconds: Total watch time in seconds
        avg_view_duration: Average view duration in seconds
        reach: Reach count
        impressions: Impression count
        click_through_rate: Click-through rate percentage
        follower_change: Change in followers
        raw_data: Raw API response for debugging
        error: Error message if fetch failed
    """
    success: bool
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    watch_time_seconds: int = 0
    avg_view_duration: float = 0.0
    reach: int = 0
    impressions: int = 0
    click_through_rate: float = 0.0
    follower_change: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseFetcher(ABC):
    """
    Abstract base class for platform analytics fetchers.
    
    Each platform implementation should:
    1. Handle OAuth token refresh if needed
    2. Call the platform's analytics API
    3. Parse and normalize the response
    4. Return a FetchResult
    """
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        """
        Initialize the fetcher.
        
        Args:
            access_token: OAuth access token
            refresh_token: Optional refresh token for token renewal
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name."""
        pass
    
    @abstractmethod
    async def fetch_video_analytics(self, video_id: str) -> FetchResult:
        """
        Fetch analytics for a specific video.
        
        Args:
            video_id: Platform-specific video ID
            
        Returns:
            FetchResult with analytics data
        """
        pass
    
    @abstractmethod
    async def fetch_channel_analytics(self) -> Dict[str, Any]:
        """
        Fetch overall channel/account analytics.
        
        Returns:
            Dictionary with channel-level metrics
        """
        pass
    
    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the access token if needed.
        
        Override in subclasses that support token refresh.
        
        Returns:
            New access token if refreshed, None otherwise
        """
        return None
    
    def _log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log an error with context."""
        logger.error(f"[{self.platform_name}] {error}", extra=context or {})
    
    def _log_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log an info message with context."""
        logger.info(f"[{self.platform_name}] {message}", extra=context or {})

