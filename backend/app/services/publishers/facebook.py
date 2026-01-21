"""
Facebook Publisher

Handles publishing videos to Facebook Pages.
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.publishers.base import BasePublisher, PublishRequest, PublishResult
from app.integrations.social.facebook import FacebookClient

logger = logging.getLogger(__name__)


class FacebookPublisher(BasePublisher):
    """
    Facebook video publisher.
    
    Uses the Meta Graph API for Facebook Page videos.
    Note: Requires a Facebook Page (not personal profile).
    """
    
    @property
    def platform_name(self) -> str:
        return "facebook"
    
    @property
    def max_title_length(self) -> int:
        return 100
    
    @property
    def max_description_length(self) -> int:
        return 5000  # Facebook description limit
    
    @property
    def max_hashtags(self) -> int:
        return 30
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a video to a Facebook Page.
        
        Args:
            request: Publish request
            
        Returns:
            PublishResult
        """
        client = FacebookClient()
        
        try:
            # Get platform-specific overrides
            overrides = request.platform_overrides or {}
            
            # Prepare metadata
            title = self.truncate_text(request.title, self.max_title_length)
            description = self._format_description(
                request.description,
                request.hashtags,
            )
            
            # Upload video
            result = await client.upload_video(
                access_token=request.access_token,
                video_path=request.video_path,
                title=title,
                description=description,
                page_id=overrides.get("page_id"),
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
            logger.exception("Facebook publish error")
            return PublishResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )
        finally:
            await client.close()
    
    def _format_description(
        self,
        description: str,
        hashtags: List[str],
    ) -> str:
        """Format Facebook description with hashtags."""
        parts = [description] if description else []
        
        if hashtags:
            hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags[:self.max_hashtags])
            parts.append(hashtag_str)
        
        full_description = "\n\n".join(parts)
        return self.truncate_text(full_description, self.max_description_length)

