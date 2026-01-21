"""
Analytics Fetchers Package

Platform-specific analytics fetching implementations.
"""

from app.services.analytics_fetchers.base import BaseFetcher, FetchResult
from app.services.analytics_fetchers.youtube import YouTubeAnalyticsFetcher
from app.services.analytics_fetchers.tiktok import TikTokAnalyticsFetcher
from app.services.analytics_fetchers.instagram import InstagramAnalyticsFetcher
from app.services.analytics_fetchers.facebook import FacebookAnalyticsFetcher

__all__ = [
    "BaseFetcher",
    "FetchResult",
    "YouTubeAnalyticsFetcher",
    "TikTokAnalyticsFetcher",
    "InstagramAnalyticsFetcher",
    "FacebookAnalyticsFetcher",
    "get_fetcher",
]


def get_fetcher(platform: str) -> type:
    """
    Get the appropriate fetcher class for a platform.
    
    Args:
        platform: Platform name (youtube, tiktok, instagram, facebook)
        
    Returns:
        Fetcher class
        
    Raises:
        ValueError: If platform is not supported
    """
    fetchers = {
        "youtube": YouTubeAnalyticsFetcher,
        "tiktok": TikTokAnalyticsFetcher,
        "instagram": InstagramAnalyticsFetcher,
        "facebook": FacebookAnalyticsFetcher,
    }
    
    if platform.lower() not in fetchers:
        raise ValueError(f"Unsupported platform: {platform}")
    
    return fetchers[platform.lower()]

