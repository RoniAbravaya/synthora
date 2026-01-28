"""
Base Provider Classes

Defines the abstract base class and types for all video generation providers.
Each provider implements the execute() method to perform its specific task.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from uuid import UUID

import httpx

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProviderCapability(str, Enum):
    """Capabilities that providers may support."""
    SCRIPT_GENERATION = "script_generation"
    VOICE_GENERATION = "voice_generation"
    VOICE_TIMING = "voice_timing"  # Returns word/sentence timestamps
    MEDIA_SEARCH = "media_search"
    MEDIA_DOWNLOAD = "media_download"
    VIDEO_GENERATION = "video_generation"
    VIDEO_ASSEMBLY = "video_assembly"
    SUBTITLE_BURNING = "subtitle_burning"


@dataclass
class TimingSegment:
    """
    A segment of text with timing information.
    Used for subtitle synchronization.
    """
    text: str
    start_ms: int
    end_ms: int
    
    @property
    def duration_ms(self) -> int:
        """Duration of this segment in milliseconds."""
        return self.end_ms - self.start_ms
    
    def to_srt_time(self, ms: int) -> str:
        """Convert milliseconds to SRT time format (HH:MM:SS,mmm)."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    
    def to_srt_entry(self, index: int) -> str:
        """Convert to SRT subtitle entry format."""
        return (
            f"{index}\n"
            f"{self.to_srt_time(self.start_ms)} --> {self.to_srt_time(self.end_ms)}\n"
            f"{self.text}\n"
        )


@dataclass
class ProviderResult:
    """
    Result of a provider execution.
    
    Attributes:
        success: Whether the operation succeeded
        data: Result data (varies by provider type)
        error: Error message if failed
        error_details: Additional error context
        duration_ms: Execution time in milliseconds
        provider_name: Name of the provider used
        raw_response: Raw API response (for debugging)
        timing_segments: Timing data for subtitles (voice providers)
    """
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    duration_ms: int = 0
    provider_name: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    timing_segments: Optional[List[TimingSegment]] = None
    
    @classmethod
    def success_result(
        cls,
        data: Dict[str, Any],
        provider_name: str,
        duration_ms: int = 0,
        timing_segments: List[TimingSegment] = None,
        raw_response: Dict[str, Any] = None,
    ) -> "ProviderResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            provider_name=provider_name,
            duration_ms=duration_ms,
            timing_segments=timing_segments,
            raw_response=raw_response,
        )
    
    @classmethod
    def failure_result(
        cls,
        error: str,
        provider_name: str,
        error_details: Dict[str, Any] = None,
        duration_ms: int = 0,
    ) -> "ProviderResult":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            error_details=error_details,
            provider_name=provider_name,
            duration_ms=duration_ms,
        )


@dataclass
class ProviderConfig:
    """
    Configuration for provider execution.
    
    Contains all the settings needed to execute a provider task.
    """
    # User and video context
    user_id: Optional[UUID] = None
    video_id: Optional[UUID] = None
    
    # Template settings
    template_config: Dict[str, Any] = field(default_factory=dict)
    
    # Generation settings
    target_duration: int = 30  # seconds
    aspect_ratio: str = "9:16"
    num_scenes: int = 5
    
    # Voice settings
    voice_gender: str = "female"
    voice_tone: str = "friendly"
    voice_speed: float = 1.0
    
    # Visual settings
    visual_style: str = "modern"
    color_palette: Optional[str] = None
    
    # Subtitle settings
    subtitle_style: str = "modern"
    include_subtitles: bool = True


class BaseProvider(ABC):
    """
    Abstract base class for all video generation providers.
    
    Each provider implementation must:
    1. Set provider_name class attribute
    2. Set category class attribute
    3. Set capabilities list
    4. Implement execute() method
    5. Optionally implement validate_api_key()
    
    Attributes:
        provider_name: Unique identifier for this provider
        category: Provider category (script, voice, media, video_ai, assembly)
        capabilities: List of capabilities this provider supports
        timeout: Default request timeout in seconds
    """
    
    provider_name: str = "base"
    category: str = "unknown"
    capabilities: List[ProviderCapability] = []
    timeout: int = 60
    
    def __init__(
        self,
        api_key: str,
        db: Optional["Session"] = None,
        config: Optional[ProviderConfig] = None,
    ):
        """
        Initialize the provider.
        
        Args:
            api_key: API key for authentication
            db: Optional database session for logging
            config: Optional provider configuration
        """
        self.api_key = api_key
        self.db = db
        self.config = config or ProviderConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._start_time: Optional[float] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._get_default_headers(),
            )
        return self._client
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests. Override in subclasses."""
        return {
            "Content-Type": "application/json",
        }
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_elapsed_ms(self) -> int:
        """Get elapsed time since start in milliseconds."""
        if self._start_time is None:
            return 0
        return int((time.time() - self._start_time) * 1000)
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """
        Execute the provider's main task.
        
        Args:
            input_data: Input data specific to the provider type
            
        Returns:
            ProviderResult with operation outcome
        """
        pass
    
    async def validate_api_key(self) -> bool:
        """
        Validate the API key.
        
        Override in subclasses to implement provider-specific validation.
        
        Returns:
            True if API key is valid
        """
        return True
    
    def _success(
        self,
        data: Dict[str, Any],
        timing_segments: List[TimingSegment] = None,
        raw_response: Dict[str, Any] = None,
    ) -> ProviderResult:
        """Create a successful result."""
        return ProviderResult.success_result(
            data=data,
            provider_name=self.provider_name,
            duration_ms=self._get_elapsed_ms(),
            timing_segments=timing_segments,
            raw_response=raw_response,
        )
    
    def _failure(
        self,
        error: str,
        error_details: Dict[str, Any] = None,
    ) -> ProviderResult:
        """Create a failed result."""
        return ProviderResult.failure_result(
            error=error,
            provider_name=self.provider_name,
            error_details=error_details,
            duration_ms=self._get_elapsed_ms(),
        )
    
    def _handle_http_error(
        self,
        status_code: int,
        response_text: str,
    ) -> ProviderResult:
        """Handle common HTTP errors."""
        error_messages = {
            400: "Bad request - check input parameters",
            401: "Invalid API key",
            403: "API key doesn't have required permissions",
            404: "Resource not found",
            429: "Rate limit exceeded - try again later",
            500: "Provider service error",
            502: "Provider service temporarily unavailable",
            503: "Provider service temporarily unavailable",
        }
        
        message = error_messages.get(status_code, f"Request failed with status {status_code}")
        
        return self._failure(
            error=message,
            error_details={
                "status_code": status_code,
                "response": response_text[:500] if response_text else None,
            },
        )
    
    async def _log_request(
        self,
        endpoint: str,
        method: str,
        request_body: Dict[str, Any],
        status_code: int,
        response_body: Dict[str, Any],
        duration_ms: int,
        error_message: str = None,
        error_details: Dict[str, Any] = None,
    ) -> None:
        """
        Log an API request to the database.
        
        Requires db session to be set.
        """
        if self.db is None:
            return
        
        try:
            from app.models.api_request_log import APIRequestLog, mask_sensitive_data, truncate_response
            
            log = APIRequestLog(
                user_id=self.config.user_id,
                video_id=self.config.video_id,
                provider=self.provider_name,
                endpoint=endpoint,
                method=method,
                request_body=mask_sensitive_data(request_body) if request_body else None,
                status_code=status_code,
                response_body=truncate_response(response_body) if response_body else None,
                duration_ms=duration_ms,
                error_message=error_message,
                error_details=error_details,
                generation_step=self.category,
            )
            
            self.db.add(log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log API request: {e}")


class ScriptProvider(BaseProvider):
    """Base class for script generation providers."""
    category = "script"
    capabilities = [ProviderCapability.SCRIPT_GENERATION]
    
    @abstractmethod
    async def generate_script(
        self,
        prompt: str,
        num_scenes: int = 5,
        target_duration: int = 30,
    ) -> ProviderResult:
        """
        Generate a video script.
        
        Args:
            prompt: User's topic/prompt
            num_scenes: Number of scenes to generate
            target_duration: Target video duration in seconds
            
        Returns:
            ProviderResult with script data including:
            - title: Video title
            - hook: Opening hook text
            - scenes: List of scene objects with narration, visual_prompt, duration
            - cta: Call-to-action text
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """Execute script generation."""
        return await self.generate_script(
            prompt=input_data.get("prompt", ""),
            num_scenes=input_data.get("num_scenes", self.config.num_scenes),
            target_duration=input_data.get("target_duration", self.config.target_duration),
        )


class VoiceProvider(BaseProvider):
    """Base class for voice/TTS providers."""
    category = "voice"
    capabilities = [ProviderCapability.VOICE_GENERATION]
    
    @abstractmethod
    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> ProviderResult:
        """
        Generate voice audio from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional specific voice to use
            
        Returns:
            ProviderResult with:
            - audio_url: URL to generated audio file
            - duration_seconds: Audio duration
            - timing_segments: Word/sentence timing for subtitles
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """Execute voice generation."""
        return await self.generate_voice(
            text=input_data.get("text", ""),
            voice_id=input_data.get("voice_id"),
        )


class MediaProvider(BaseProvider):
    """Base class for stock media providers."""
    category = "media"
    capabilities = [ProviderCapability.MEDIA_SEARCH, ProviderCapability.MEDIA_DOWNLOAD]
    
    @abstractmethod
    async def search_media(
        self,
        query: str,
        media_type: str = "video",
        count: int = 5,
    ) -> ProviderResult:
        """
        Search for stock media.
        
        Args:
            query: Search query
            media_type: "video" or "image"
            count: Number of results to return
            
        Returns:
            ProviderResult with:
            - items: List of media items with url, thumbnail, duration, etc.
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """Execute media search."""
        return await self.search_media(
            query=input_data.get("query", ""),
            media_type=input_data.get("media_type", "video"),
            count=input_data.get("count", 5),
        )


class VideoAIProvider(BaseProvider):
    """Base class for AI video generation providers."""
    category = "video_ai"
    capabilities = [ProviderCapability.VIDEO_GENERATION]
    timeout = 300  # Video generation can take a while
    
    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> ProviderResult:
        """
        Generate AI video from prompt.
        
        Args:
            prompt: Visual description prompt
            duration: Video duration in seconds
            aspect_ratio: Aspect ratio (e.g., "9:16", "16:9")
            
        Returns:
            ProviderResult with:
            - video_url: URL to generated video
            - duration_seconds: Actual video duration
            - thumbnail_url: Optional thumbnail
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """Execute video generation."""
        return await self.generate_video(
            prompt=input_data.get("prompt", ""),
            duration=input_data.get("duration", 5),
            aspect_ratio=input_data.get("aspect_ratio", self.config.aspect_ratio),
        )


class AssemblyProvider(BaseProvider):
    """Base class for video assembly providers."""
    category = "assembly"
    capabilities = [ProviderCapability.VIDEO_ASSEMBLY, ProviderCapability.SUBTITLE_BURNING]
    timeout = 600  # Assembly can take a while
    
    @abstractmethod
    async def assemble_video(
        self,
        scenes: List[Dict[str, Any]],
        audio_url: str,
        subtitle_file: Optional[str] = None,
    ) -> ProviderResult:
        """
        Assemble final video from components.
        
        Args:
            scenes: List of scene data with media URLs
            audio_url: URL to voiceover audio
            subtitle_file: Optional path to subtitle file
            
        Returns:
            ProviderResult with:
            - video_url: URL to final video
            - thumbnail_url: Video thumbnail
            - duration_seconds: Video duration
            - file_size: File size in bytes
            - resolution: Video resolution string
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> ProviderResult:
        """Execute video assembly."""
        return await self.assemble_video(
            scenes=input_data.get("scenes", []),
            audio_url=input_data.get("audio_url", ""),
            subtitle_file=input_data.get("subtitle_file"),
        )
