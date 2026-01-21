"""
TikTok Publisher

Handles publishing videos to TikTok.
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.publishers.base import BasePublisher, PublishRequest, PublishResult
from app.integrations.social.tiktok import TikTokClient

logger = logging.getLogger(__name__)


class TikTokPublisher(BasePublisher):
    """
    TikTok video publisher.
    
    Uses the TikTok Content Posting API.
    """
    
    @property
    def platform_name(self) -> str:
        return "tiktok"
    
    @property
    def max_title_length(self) -> int:
        return 150  # TikTok doesn't have a separate title
    
    @property
    def max_description_length(self) -> int:
        return 2200  # TikTok caption limit
    
    @property
    def max_hashtags(self) -> int:
        return 30  # TikTok allows many hashtags
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a video to TikTok.
        
        Args:
            request: Publish request
            
        Returns:
            PublishResult
        """
        client = TikTokClient()
        
        try:
            # Get platform-specific overrides
            overrides = request.platform_overrides or {}
            
            # TikTok uses a single caption field
            caption = self.format_caption(
                request.title,
                request.description,
                request.hashtags,
            )
            caption = self.truncate_text(caption, self.max_description_length)
            
            # Upload video
            result = await client.upload_video(
                access_token=request.access_token,
                video_path=request.video_path,
                title=request.title,
                description=caption,
                privacy_level=overrides.get("privacy_level", "PUBLIC_TO_EVERYONE"),
                disable_duet=overrides.get("disable_duet", False),
                disable_comment=overrides.get("disable_comment", False),
                disable_stitch=overrides.get("disable_stitch", False),
            )
            
            if result.success:
                return PublishResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=result.post_id,
                    post_url=result.post_url,
                    metadata={
                        "status": "processing",
                        "message": "Video uploaded, TikTok is processing",
                        **(result.metadata or {}),
                    },
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform_name,
                    error=result.error,
                )
                
        except Exception as e:
            logger.exception("TikTok publish error")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )
        finally:
            await client.close()

