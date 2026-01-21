"""
Instagram Publisher

Handles publishing videos to Instagram (Reels).
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.publishers.base import BasePublisher, PublishRequest, PublishResult
from app.integrations.social.instagram import InstagramClient

logger = logging.getLogger(__name__)


class InstagramPublisher(BasePublisher):
    """
    Instagram video publisher.
    
    Uses the Meta Graph API for Instagram Reels.
    Note: Requires a public video URL.
    """
    
    @property
    def platform_name(self) -> str:
        return "instagram"
    
    @property
    def max_title_length(self) -> int:
        return 0  # Instagram doesn't have titles
    
    @property
    def max_description_length(self) -> int:
        return 2200  # Instagram caption limit
    
    @property
    def max_hashtags(self) -> int:
        return 30  # Instagram allows up to 30 hashtags
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a video to Instagram as a Reel.
        
        Args:
            request: Publish request
            
        Returns:
            PublishResult
        """
        # Instagram requires a public video URL
        if not request.video_url:
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error="Instagram requires a public video URL",
            )
        
        client = InstagramClient()
        
        try:
            # Get platform-specific overrides
            overrides = request.platform_overrides or {}
            
            # Instagram uses a single caption field
            caption = self.format_caption(
                "",  # No title for Instagram
                request.description,
                request.hashtags,
            )
            caption = self.truncate_text(caption, self.max_description_length)
            
            # Upload video
            result = await client.upload_video(
                access_token=request.access_token,
                video_path=request.video_path,
                title="",
                description=caption,
                video_url=request.video_url,
            )
            
            if result.success:
                return PublishResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=result.post_id,
                    post_url=result.post_url,
                    metadata=result.metadata,
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=result.error,
                )
                
        except Exception as e:
            logger.exception("Instagram publish error")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )
        finally:
            await client.close()

