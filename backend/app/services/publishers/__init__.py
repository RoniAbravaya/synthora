"""
Platform Publishers

Handles publishing videos to various social media platforms.
"""

from app.services.publishers.base import BasePublisher, PublishResult
from app.services.publishers.youtube import YouTubePublisher
from app.services.publishers.tiktok import TikTokPublisher
from app.services.publishers.instagram import InstagramPublisher
from app.services.publishers.facebook import FacebookPublisher

from app.models.social_account import SocialPlatform


def get_publisher(platform: SocialPlatform) -> BasePublisher:
    """
    Get the appropriate publisher for a platform.
    
    Args:
        platform: Social platform
        
    Returns:
        Platform-specific publisher instance
    """
    publishers = {
        SocialPlatform.YOUTUBE: YouTubePublisher,
        SocialPlatform.TIKTOK: TikTokPublisher,
        SocialPlatform.INSTAGRAM: InstagramPublisher,
        SocialPlatform.FACEBOOK: FacebookPublisher,
    }
    
    publisher_class = publishers.get(platform)
    if not publisher_class:
        raise ValueError(f"Unsupported platform: {platform.value}")
    
    return publisher_class()


__all__ = [
    "get_publisher",
    "BasePublisher",
    "PublishResult",
    "YouTubePublisher",
    "TikTokPublisher",
    "InstagramPublisher",
    "FacebookPublisher",
]

