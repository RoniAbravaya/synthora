"""
YouTube Publisher

Handles publishing videos to YouTube.
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.publishers.base import BasePublisher, PublishRequest, PublishResult
from app.integrations.social.youtube import YouTubeClient

logger = logging.getLogger(__name__)


class YouTubePublisher(BasePublisher):
    """
    YouTube video publisher.
    
    Uses the YouTube Data API to upload videos.
    """
    
    @property
    def platform_name(self) -> str:
        return "youtube"
    
    @property
    def max_title_length(self) -> int:
        return 100
    
    @property
    def max_description_length(self) -> int:
        return 5000
    
    @property
    def max_hashtags(self) -> int:
        return 15  # YouTube allows up to 15 hashtags
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a video to YouTube.
        
        Args:
            request: Publish request
            
        Returns:
            PublishResult
        """
        client = YouTubeClient()
        
        try:
            # Get platform-specific overrides
            overrides = request.platform_overrides or {}
            
            # Prepare metadata
            title = self.truncate_text(request.title, self.max_title_length)
            description = self._format_description(
                request.description,
                request.hashtags,
            )
            
            # Get tags (hashtags without #)
            tags = [tag.lstrip("#") for tag in request.hashtags[:self.max_hashtags]]
            
            # Upload video
            result = await client.upload_video(
                access_token=request.access_token,
                video_path=request.video_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=overrides.get("privacy_status", "public"),
                category_id=overrides.get("category_id", "22"),  # People & Blogs
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
            logger.exception("YouTube publish error")
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
        """Format YouTube description with hashtags."""
        parts = [description] if description else []
        
        if hashtags:
            # YouTube shows first 3 hashtags above title
            hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags[:self.max_hashtags])
            parts.append(hashtag_str)
        
        full_description = "\n\n".join(parts)
        return self.truncate_text(full_description, self.max_description_length)

