"""
Pexels Media Provider

Fetches stock videos and images from Pexels API.
Free to use with attribution.
"""

import logging
import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import httpx

from app.integrations.providers.base import (
    MediaProvider,
    ProviderResult,
    ProviderCapability,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.integrations.providers.base import ProviderConfig

logger = logging.getLogger(__name__)


class PexelsProvider(MediaProvider):
    """
    Pexels provider for stock media.
    
    Features:
    - Free stock videos and images
    - High-quality media
    - Multiple resolutions available
    """
    
    provider_name = "pexels"
    category = "media"
    capabilities = [
        ProviderCapability.MEDIA_SEARCH,
        ProviderCapability.MEDIA_DOWNLOAD,
    ]
    timeout = 30
    
    # API Configuration
    BASE_URL = "https://api.pexels.com"
    
    def __init__(
        self,
        api_key: str,
        db: Optional["Session"] = None,
        config: Optional["ProviderConfig"] = None,
    ):
        """Initialize the Pexels provider."""
        super().__init__(api_key, db, config)
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers for Pexels API requests."""
        return {
            "Authorization": self.api_key,
        }
    
    async def search_media(
        self,
        query: str,
        media_type: str = "video",
        count: int = 5,
    ) -> ProviderResult:
        """
        Search for stock media on Pexels.
        
        Args:
            query: Search query
            media_type: "video" or "image"
            count: Number of results to return
            
        Returns:
            ProviderResult with media items
        """
        self._start_time = time.time()
        
        if media_type == "video":
            return await self._search_videos(query, count)
        else:
            return await self._search_images(query, count)
    
    async def _search_videos(
        self,
        query: str,
        count: int,
    ) -> ProviderResult:
        """Search for videos on Pexels."""
        # Determine orientation from aspect ratio
        orientation = "portrait"
        if self.config:
            aspect_ratio = self.config.aspect_ratio
            if aspect_ratio in ["16:9", "4:3"]:
                orientation = "landscape"
            elif aspect_ratio == "1:1":
                orientation = "square"
        
        endpoint = f"{self.BASE_URL}/videos/search"
        params = {
            "query": query,
            "per_page": count,
            "orientation": orientation,
        }
        
        try:
            response = await self.client.get(
                endpoint,
                params=params,
                headers=self._get_default_headers(),
            )
            
            await self._log_request(
                endpoint=endpoint,
                method="GET",
                request_body=params,
                status_code=response.status_code,
                response_body=response.json() if response.status_code == 200 else None,
                duration_ms=self._get_elapsed_ms(),
            )
            
            if response.status_code != 200:
                return self._handle_http_error(response.status_code, response.text)
            
            data = response.json()
            videos = data.get("videos", [])
            
            # Transform to standard format
            items = []
            for video in videos:
                # Get best quality video file
                video_files = video.get("video_files", [])
                best_file = self._get_best_video_file(video_files, orientation)
                
                if best_file:
                    items.append({
                        "id": str(video.get("id")),
                        "type": "video",
                        "url": best_file.get("link"),
                        "thumbnail_url": video.get("image"),
                        "width": best_file.get("width"),
                        "height": best_file.get("height"),
                        "duration_seconds": video.get("duration"),
                        "photographer": video.get("user", {}).get("name"),
                        "source": "pexels",
                        "source_url": video.get("url"),
                    })
            
            return self._success(
                data={
                    "items": items,
                    "total_results": data.get("total_results", len(items)),
                    "query": query,
                    "media_type": "video",
                    "provider": self.provider_name,
                },
            )
            
        except httpx.RequestError as e:
            logger.error(f"Pexels API request failed: {e}")
            return self._failure(
                error=f"API request failed: {str(e)}",
                error_details={"exception": type(e).__name__},
            )
        except Exception as e:
            logger.exception(f"Video search failed: {e}")
            return self._failure(
                error=str(e),
                error_details={"exception": type(e).__name__},
            )
    
    async def _search_images(
        self,
        query: str,
        count: int,
    ) -> ProviderResult:
        """Search for images on Pexels."""
        orientation = "portrait"
        if self.config:
            aspect_ratio = self.config.aspect_ratio
            if aspect_ratio in ["16:9", "4:3"]:
                orientation = "landscape"
            elif aspect_ratio == "1:1":
                orientation = "square"
        
        endpoint = f"{self.BASE_URL}/v1/search"
        params = {
            "query": query,
            "per_page": count,
            "orientation": orientation,
        }
        
        try:
            response = await self.client.get(
                endpoint,
                params=params,
                headers=self._get_default_headers(),
            )
            
            await self._log_request(
                endpoint=endpoint,
                method="GET",
                request_body=params,
                status_code=response.status_code,
                response_body=response.json() if response.status_code == 200 else None,
                duration_ms=self._get_elapsed_ms(),
            )
            
            if response.status_code != 200:
                return self._handle_http_error(response.status_code, response.text)
            
            data = response.json()
            photos = data.get("photos", [])
            
            items = []
            for photo in photos:
                src = photo.get("src", {})
                items.append({
                    "id": str(photo.get("id")),
                    "type": "image",
                    "url": src.get("original"),
                    "thumbnail_url": src.get("medium"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "photographer": photo.get("photographer"),
                    "source": "pexels",
                    "source_url": photo.get("url"),
                })
            
            return self._success(
                data={
                    "items": items,
                    "total_results": data.get("total_results", len(items)),
                    "query": query,
                    "media_type": "image",
                    "provider": self.provider_name,
                },
            )
            
        except httpx.RequestError as e:
            logger.error(f"Pexels API request failed: {e}")
            return self._failure(
                error=f"API request failed: {str(e)}",
                error_details={"exception": type(e).__name__},
            )
        except Exception as e:
            logger.exception(f"Image search failed: {e}")
            return self._failure(
                error=str(e),
                error_details={"exception": type(e).__name__},
            )
    
    def _get_best_video_file(
        self,
        video_files: List[Dict[str, Any]],
        orientation: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best quality video file for the given orientation.
        
        Prefers HD quality (720p-1080p) over 4K for balance of quality and size.
        """
        if not video_files:
            return None
        
        # Target resolution based on orientation
        if orientation == "portrait":
            target_height = 1920
            target_width = 1080
        elif orientation == "landscape":
            target_height = 1080
            target_width = 1920
        else:
            target_height = 1080
            target_width = 1080
        
        # Sort by quality (prefer HD)
        def quality_score(f):
            width = f.get("width", 0)
            height = f.get("height", 0)
            
            # Prefer files close to target resolution
            width_diff = abs(width - target_width)
            height_diff = abs(height - target_height)
            
            # Penalize very low or very high resolutions
            if height < 480:
                return 10000 + height_diff
            if height > 2160:
                return 5000 + height_diff
            
            return width_diff + height_diff
        
        sorted_files = sorted(video_files, key=quality_score)
        return sorted_files[0] if sorted_files else None
    
    async def validate_api_key(self) -> bool:
        """Validate the Pexels API key."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/v1/search",
                params={"query": "test", "per_page": 1},
                headers=self._get_default_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
