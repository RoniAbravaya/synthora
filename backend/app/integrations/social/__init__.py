"""
Social Media Platform Integrations

OAuth clients and API wrappers for social media platforms.
"""

from typing import Optional

from app.models.social_account import SocialPlatform
from app.integrations.social.base import BaseSocialClient
from app.integrations.social.youtube import YouTubeClient
from app.integrations.social.tiktok import TikTokClient
from app.integrations.social.instagram import InstagramClient
from app.integrations.social.facebook import FacebookClient


def get_platform_client(platform: SocialPlatform) -> BaseSocialClient:
    """
    Get the appropriate client for a social platform.
    
    Args:
        platform: Social platform enum
        
    Returns:
        Platform-specific client instance
        
    Raises:
        ValueError: If platform is not supported
    """
    clients = {
        SocialPlatform.YOUTUBE: YouTubeClient,
        SocialPlatform.TIKTOK: TikTokClient,
        SocialPlatform.INSTAGRAM: InstagramClient,
        SocialPlatform.FACEBOOK: FacebookClient,
    }
    
    client_class = clients.get(platform)
    if not client_class:
        raise ValueError(f"Unsupported platform: {platform.value}")
    
    return client_class()


__all__ = [
    "get_platform_client",
    "BaseSocialClient",
    "YouTubeClient",
    "TikTokClient",
    "InstagramClient",
    "FacebookClient",
]

