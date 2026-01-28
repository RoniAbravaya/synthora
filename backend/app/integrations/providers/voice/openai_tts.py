"""
OpenAI TTS Voice Provider

Generates voice audio using OpenAI's Text-to-Speech API.
Note: OpenAI TTS does not provide timing data, so timing is estimated.
"""

import logging
import time
import base64
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import re

import httpx

from app.integrations.providers.base import (
    VoiceProvider,
    ProviderResult,
    ProviderCapability,
    TimingSegment,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.integrations.providers.base import ProviderConfig

logger = logging.getLogger(__name__)


class OpenAITTSProvider(VoiceProvider):
    """
    OpenAI TTS provider for voice generation.
    
    Uses OpenAI's text-to-speech API with multiple voice options.
    Note: Timing is estimated since OpenAI doesn't provide timestamps.
    """
    
    provider_name = "openai_tts"
    category = "voice"
    capabilities = [ProviderCapability.VOICE_GENERATION]
    timeout = 120
    
    # API Configuration
    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "tts-1-hd"
    
    # Available voices
    VOICES = {
        "alloy": "neutral",
        "echo": "male",
        "fable": "male",
        "onyx": "male",
        "nova": "female",
        "shimmer": "female",
    }
    
    # Default voice by gender
    DEFAULT_VOICE = {
        "female": "nova",
        "male": "onyx",
    }
    
    def __init__(
        self,
        api_key: str,
        db: Optional["Session"] = None,
        config: Optional["ProviderConfig"] = None,
    ):
        """Initialize the OpenAI TTS provider."""
        super().__init__(api_key, db, config)
        self.model = self.DEFAULT_MODEL
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
        }
    
    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> ProviderResult:
        """
        Generate voice audio from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice name (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            ProviderResult with audio data and estimated timing
        """
        self._start_time = time.time()
        
        # Select voice
        if not voice_id:
            voice_gender = self.config.voice_gender if self.config else "female"
            voice_id = self.DEFAULT_VOICE.get(voice_gender, "nova")
        
        # Validate voice
        if voice_id not in self.VOICES:
            voice_id = "nova"
        
        endpoint = f"{self.BASE_URL}/audio/speech"
        
        # Get voice speed from config
        speed = 1.0
        if self.config:
            speed = self.config.voice_speed
        
        request_body = {
            "model": self.model,
            "input": text,
            "voice": voice_id,
            "response_format": "mp3",
            "speed": speed,
        }
        
        try:
            response = await self.client.post(
                endpoint,
                json=request_body,
                headers={
                    **self._get_default_headers(),
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code != 200:
                await self._log_request(
                    endpoint=endpoint,
                    method="POST",
                    request_body=request_body,
                    status_code=response.status_code,
                    response_body=None,
                    duration_ms=self._get_elapsed_ms(),
                    error_message=response.text,
                )
                return self._handle_http_error(response.status_code, response.text)
            
            # Get audio data
            audio_data = response.content
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")
            
            # Estimate duration based on text length and speed
            # Average: ~150 words per minute at speed 1.0
            words = len(text.split())
            duration_seconds = (words / 150) * 60 / speed
            
            # Estimate timing segments
            timing_segments = self._estimate_timing(text, duration_seconds)
            
            await self._log_request(
                endpoint=endpoint,
                method="POST",
                request_body=request_body,
                status_code=response.status_code,
                response_body={"audio_size_bytes": len(audio_data)},
                duration_ms=self._get_elapsed_ms(),
            )
            
            return self._success(
                data={
                    "audio_base64": audio_base64,
                    "audio_format": "mp3",
                    "duration_seconds": duration_seconds,
                    "voice_id": voice_id,
                    "model": self.model,
                    "provider": self.provider_name,
                    "text": text,
                },
                timing_segments=timing_segments,
            )
            
        except httpx.RequestError as e:
            logger.error(f"OpenAI TTS API request failed: {e}")
            return self._failure(
                error=f"API request failed: {str(e)}",
                error_details={"exception": type(e).__name__},
            )
        except Exception as e:
            logger.exception(f"Voice generation failed: {e}")
            return self._failure(
                error=str(e),
                error_details={"exception": type(e).__name__},
            )
    
    def _estimate_timing(
        self,
        text: str,
        total_duration_seconds: float,
    ) -> List[TimingSegment]:
        """
        Estimate timing segments for subtitles.
        
        Since OpenAI TTS doesn't provide timing, we estimate
        based on text length and total duration.
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [TimingSegment(
                text=text,
                start_ms=0,
                end_ms=int(total_duration_seconds * 1000),
            )]
        
        # Distribute time proportionally by character count
        total_chars = sum(len(s) for s in sentences)
        total_duration_ms = int(total_duration_seconds * 1000)
        
        segments = []
        current_time = 0
        
        for sentence in sentences:
            if total_chars > 0:
                proportion = len(sentence) / total_chars
            else:
                proportion = 1 / len(sentences)
            
            duration = int(total_duration_ms * proportion)
            
            segments.append(TimingSegment(
                text=sentence,
                start_ms=current_time,
                end_ms=current_time + duration,
            ))
            current_time += duration
        
        # Adjust last segment to match total duration
        if segments:
            segments[-1].end_ms = total_duration_ms
        
        return segments
    
    async def validate_api_key(self) -> bool:
        """Validate the OpenAI API key."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/models",
                headers=self._get_default_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
