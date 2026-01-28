"""
ElevenLabs Voice Provider

Generates voice audio using ElevenLabs API.
Supports voice selection and returns timing data for subtitles.
"""

import logging
import time
import io
from typing import Dict, Any, Optional, List, TYPE_CHECKING

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


class ElevenLabsProvider(VoiceProvider):
    """
    ElevenLabs provider for voice generation.
    
    Features:
    - High-quality voice synthesis
    - Multiple voice options
    - Character-level timing for subtitles
    """
    
    provider_name = "elevenlabs"
    category = "voice"
    capabilities = [
        ProviderCapability.VOICE_GENERATION,
        ProviderCapability.VOICE_TIMING,
    ]
    timeout = 120
    
    # API Configuration
    BASE_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_MODEL = "eleven_multilingual_v2"
    
    # Default voices (premium voices from ElevenLabs)
    DEFAULT_VOICES = {
        "female": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "male": "29vD33N1CtxCmqQRPOHJ",    # Drew
    }
    
    def __init__(
        self,
        api_key: str,
        db: Optional["Session"] = None,
        config: Optional["ProviderConfig"] = None,
    ):
        """Initialize the ElevenLabs provider."""
        super().__init__(api_key, db, config)
        self.model = self.DEFAULT_MODEL
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers for ElevenLabs API requests."""
        return {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
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
            voice_id: Optional specific voice ID
            
        Returns:
            ProviderResult with audio URL and timing data
        """
        self._start_time = time.time()
        
        # Select voice
        if not voice_id:
            voice_gender = self.config.voice_gender if self.config else "female"
            voice_id = self.DEFAULT_VOICES.get(voice_gender, self.DEFAULT_VOICES["female"])
        
        endpoint = f"{self.BASE_URL}/text-to-speech/{voice_id}/with-timestamps"
        
        request_body = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }
        
        try:
            response = await self.client.post(
                endpoint,
                json=request_body,
                headers=self._get_default_headers(),
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
            
            response_data = response.json()
            
            await self._log_request(
                endpoint=endpoint,
                method="POST",
                request_body=request_body,
                status_code=response.status_code,
                response_body={"alignment": response_data.get("alignment", {})},
                duration_ms=self._get_elapsed_ms(),
            )
            
            # Get audio data (base64 encoded)
            audio_base64 = response_data.get("audio_base64", "")
            
            # Extract timing data
            alignment = response_data.get("alignment", {})
            timing_segments = self._extract_timing(alignment, text)
            
            # Calculate duration from timing
            duration_seconds = 0
            if timing_segments:
                duration_seconds = timing_segments[-1].end_ms / 1000
            
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
                raw_response={"alignment": alignment},
            )
            
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs API request failed: {e}")
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
    
    def _extract_timing(
        self,
        alignment: Dict[str, Any],
        original_text: str,
    ) -> List[TimingSegment]:
        """
        Extract timing segments from ElevenLabs alignment data.
        
        ElevenLabs provides character-level timing. We aggregate
        to sentence level for subtitles.
        """
        characters = alignment.get("characters", [])
        char_start_times = alignment.get("character_start_times_seconds", [])
        char_end_times = alignment.get("character_end_times_seconds", [])
        
        if not characters or not char_start_times:
            # Fallback: estimate timing from text
            return self._estimate_timing(original_text)
        
        segments = []
        current_sentence = ""
        sentence_start = None
        sentence_end = None
        
        sentence_enders = ".!?"
        
        for i, char in enumerate(characters):
            if sentence_start is None:
                sentence_start = char_start_times[i] if i < len(char_start_times) else 0
            
            current_sentence += char
            sentence_end = char_end_times[i] if i < len(char_end_times) else sentence_start
            
            # Check if this ends a sentence
            if char in sentence_enders and current_sentence.strip():
                segments.append(TimingSegment(
                    text=current_sentence.strip(),
                    start_ms=int(sentence_start * 1000),
                    end_ms=int(sentence_end * 1000),
                ))
                current_sentence = ""
                sentence_start = None
        
        # Add remaining text
        if current_sentence.strip():
            segments.append(TimingSegment(
                text=current_sentence.strip(),
                start_ms=int((sentence_start or 0) * 1000),
                end_ms=int((sentence_end or 0) * 1000),
            ))
        
        return segments
    
    def _estimate_timing(
        self,
        text: str,
        words_per_minute: int = 150,
    ) -> List[TimingSegment]:
        """
        Estimate timing when no alignment data is available.
        
        Assumes average speaking rate of 150 words per minute.
        """
        import re
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # Calculate total duration based on word count
        total_words = len(text.split())
        total_duration_ms = int((total_words / words_per_minute) * 60 * 1000)
        
        # Distribute time proportionally
        total_chars = sum(len(s) for s in sentences)
        current_time = 0
        segments = []
        
        for sentence in sentences:
            proportion = len(sentence) / total_chars if total_chars > 0 else 1 / len(sentences)
            duration = int(total_duration_ms * proportion)
            
            segments.append(TimingSegment(
                text=sentence,
                start_ms=current_time,
                end_ms=current_time + duration,
            ))
            current_time += duration
        
        return segments
    
    async def get_voices(self) -> List[Dict[str, Any]]:
        """
        Get available voices from ElevenLabs.
        
        Returns:
            List of voice information dictionaries
        """
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/voices",
                headers=self._get_default_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("voices", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []
    
    async def validate_api_key(self) -> bool:
        """Validate the ElevenLabs API key."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/user",
                headers=self._get_default_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
