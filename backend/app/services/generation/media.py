"""
Media Fetching Service

Fetches stock media (images and videos) for video generation.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import httpx

from app.models.integration import IntegrationProvider
from app.services.generation.pipeline import StepResult

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a single media item."""
    
    id: str
    type: str  # "image" or "video"
    url: str
    preview_url: Optional[str] = None
    width: int = 0
    height: int = 0
    duration: Optional[float] = None  # For videos
    source: str = ""
    photographer: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "url": self.url,
            "preview_url": self.preview_url,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "source": self.source,
            "photographer": self.photographer,
        }


class MediaFetcher:
    """
    Fetches stock media for video generation.
    
    Currently supports:
    - Pexels (videos and images)
    - Unsplash (images only)
    
    The fetcher analyzes the script to determine what media to fetch
    based on visual descriptions.
    """
    
    def __init__(self, api_key: str, provider: IntegrationProvider):
        """
        Initialize the media fetcher.
        
        Args:
            api_key: API key for the provider
            provider: Integration provider to use
        """
        self.api_key = api_key
        self.provider = provider
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch(
        self,
        script: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str = "9:16",
    ) -> StepResult:
        """
        Fetch media for the video.
        
        Args:
            script: Script data from script generation step
            template_config: Template configuration
            aspect_ratio: Target aspect ratio
            
        Returns:
            StepResult with media data
        """
        try:
            if self.provider == IntegrationProvider.PEXELS:
                return await self._fetch_pexels(script, template_config, aspect_ratio)
            elif self.provider == IntegrationProvider.UNSPLASH:
                return await self._fetch_unsplash(script, template_config, aspect_ratio)
            else:
                return StepResult(
                    success=False,
                    error=f"Unsupported media provider: {self.provider}",
                )
        except Exception as e:
            logger.exception("Media fetching failed")
            return StepResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )
        finally:
            await self.client.aclose()
    
    async def _fetch_pexels(
        self,
        script: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Fetch media from Pexels."""
        
        script_data = script.get("script", script)
        scenes = script_data.get("scenes", [])
        
        media_items: List[MediaItem] = []
        
        # Determine orientation based on aspect ratio
        orientation = "portrait" if aspect_ratio in ["9:16", "4:5"] else "landscape"
        
        for scene in scenes:
            visual_desc = scene.get("visual_description", "")
            
            if not visual_desc:
                continue
            
            # Extract keywords from visual description
            keywords = self._extract_keywords(visual_desc)
            
            if not keywords:
                keywords = "abstract background"
            
            # Try to fetch video first, then image
            video_item = await self._search_pexels_video(keywords, orientation)
            
            if video_item:
                media_items.append(video_item)
            else:
                # Fallback to image
                image_item = await self._search_pexels_image(keywords, orientation)
                if image_item:
                    media_items.append(image_item)
        
        if not media_items:
            return StepResult(
                success=False,
                error="No media found for any scene",
            )
        
        return StepResult(
            success=True,
            data={
                "media_items": [item.to_dict() for item in media_items],
                "total_items": len(media_items),
                "provider": self.provider,
            },
        )
    
    async def _search_pexels_video(
        self,
        query: str,
        orientation: str,
    ) -> Optional[MediaItem]:
        """Search for a video on Pexels."""
        
        response = await self.client.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": self.api_key},
            params={
                "query": query,
                "orientation": orientation,
                "per_page": 1,
            },
        )
        
        if response.status_code != 200:
            logger.warning(f"Pexels video search failed: {response.status_code}")
            return None
        
        data = response.json()
        videos = data.get("videos", [])
        
        if not videos:
            return None
        
        video = videos[0]
        
        # Get the best quality video file
        video_files = video.get("video_files", [])
        best_file = None
        for vf in video_files:
            if vf.get("quality") == "hd":
                best_file = vf
                break
        
        if not best_file and video_files:
            best_file = video_files[0]
        
        if not best_file:
            return None
        
        return MediaItem(
            id=str(video["id"]),
            type="video",
            url=best_file.get("link", ""),
            preview_url=video.get("image"),
            width=best_file.get("width", 0),
            height=best_file.get("height", 0),
            duration=video.get("duration"),
            source="pexels",
            photographer=video.get("user", {}).get("name"),
        )
    
    async def _search_pexels_image(
        self,
        query: str,
        orientation: str,
    ) -> Optional[MediaItem]:
        """Search for an image on Pexels."""
        
        response = await self.client.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": self.api_key},
            params={
                "query": query,
                "orientation": orientation,
                "per_page": 1,
            },
        )
        
        if response.status_code != 200:
            logger.warning(f"Pexels image search failed: {response.status_code}")
            return None
        
        data = response.json()
        photos = data.get("photos", [])
        
        if not photos:
            return None
        
        photo = photos[0]
        
        return MediaItem(
            id=str(photo["id"]),
            type="image",
            url=photo.get("src", {}).get("original", ""),
            preview_url=photo.get("src", {}).get("medium"),
            width=photo.get("width", 0),
            height=photo.get("height", 0),
            source="pexels",
            photographer=photo.get("photographer"),
        )
    
    async def _fetch_unsplash(
        self,
        script: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Fetch media from Unsplash (images only)."""
        
        script_data = script.get("script", script)
        scenes = script_data.get("scenes", [])
        
        media_items: List[MediaItem] = []
        
        # Determine orientation
        orientation = "portrait" if aspect_ratio in ["9:16", "4:5"] else "landscape"
        
        for scene in scenes:
            visual_desc = scene.get("visual_description", "")
            
            if not visual_desc:
                continue
            
            keywords = self._extract_keywords(visual_desc)
            
            if not keywords:
                keywords = "abstract"
            
            image_item = await self._search_unsplash(keywords, orientation)
            
            if image_item:
                media_items.append(image_item)
        
        if not media_items:
            return StepResult(
                success=False,
                error="No media found for any scene",
            )
        
        return StepResult(
            success=True,
            data={
                "media_items": [item.to_dict() for item in media_items],
                "total_items": len(media_items),
                "provider": self.provider,
            },
        )
    
    async def _search_unsplash(
        self,
        query: str,
        orientation: str,
    ) -> Optional[MediaItem]:
        """Search for an image on Unsplash."""
        
        response = await self.client.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {self.api_key}"},
            params={
                "query": query,
                "orientation": orientation,
                "per_page": 1,
            },
        )
        
        if response.status_code != 200:
            logger.warning(f"Unsplash search failed: {response.status_code}")
            return None
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return None
        
        photo = results[0]
        
        return MediaItem(
            id=photo["id"],
            type="image",
            url=photo.get("urls", {}).get("full", ""),
            preview_url=photo.get("urls", {}).get("regular"),
            width=photo.get("width", 0),
            height=photo.get("height", 0),
            source="unsplash",
            photographer=photo.get("user", {}).get("name"),
        )
    
    def _extract_keywords(self, visual_description: str) -> str:
        """
        Extract search keywords from visual description.
        
        This is a simple implementation - could be enhanced with NLP.
        """
        # Remove common filler words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can", "need",
            "showing", "show", "shows", "displayed", "display", "featuring",
            "feature", "features", "scene", "shot", "clip", "video", "image",
        }
        
        words = visual_description.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Return first 3-5 keywords
        return " ".join(keywords[:5])

