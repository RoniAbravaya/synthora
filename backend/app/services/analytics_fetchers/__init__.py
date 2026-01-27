"""
Analytics Fetchers Module

Provides fetcher classes for retrieving analytics data from social media platforms.
"""

from typing import Type, Dict

from .base import BaseFetcher, FetchResult
from .youtube import YouTubeFetcher

# Registry of available fetchers
_FETCHERS: Dict[str, Type[BaseFetcher]] = {
    "youtube": YouTubeFetcher,
}


def get_fetcher(platform: str) -> Type[BaseFetcher]:
    """
    Get the fetcher class for a platform.
    
    Args:
        platform: Platform name (e.g., 'youtube')
        
    Returns:
        Fetcher class for the platform
        
    Raises:
        ValueError: If platform is not supported
    """
    # Handle both string and enum
    platform_name = platform.value if hasattr(platform, 'value') else platform
    
    fetcher_class = _FETCHERS.get(platform_name.lower())
    if not fetcher_class:
        raise ValueError(f"No analytics fetcher for platform: {platform_name}")
    
    return fetcher_class


__all__ = [
    "BaseFetcher",
    "FetchResult",
    "YouTubeFetcher",
    "get_fetcher",
]
