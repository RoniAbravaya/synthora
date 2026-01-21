"""
Voice Generation Service

Generates voice-over audio using AI (ElevenLabs).
"""

import logging
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx

from app.models.integration import IntegrationProvider
from app.services.generation.pipeline import StepResult

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Voice configuration settings."""
    
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


# Default voice IDs for ElevenLabs
ELEVENLABS_VOICES = {
    "male": {
        "professional": "pNInz6obpgDQGcFmaJgB",  # Adam
        "casual": "VR6AewLTigWG4xSOukaG",  # Arnold
        "energetic": "ErXwobaYiN019PkySvjV",  # Antoni
        "dramatic": "TxGEqnHWrfWFTfGW9XjX",  # Josh
    },
    "female": {
        "professional": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "casual": "EXAVITQu4vr4xnSDxMaL",  # Bella
        "energetic": "MF3mGyEYCl7XYWbV9V6O",  # Emily
        "dramatic": "XrExE9yKIg1WjnnlVkGX",  # Matilda
    },
    "neutral": {
        "professional": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "casual": "pNInz6obpgDQGcFmaJgB",  # Adam
        "energetic": "ErXwobaYiN019PkySvjV",  # Antoni
        "dramatic": "TxGEqnHWrfWFTfGW9XjX",  # Josh
    },
}


class VoiceGenerator:
    """
    Generates voice-over audio using AI.
    
    Currently supports:
    - ElevenLabs
    
    The generator uses template configuration to customize voice
    characteristics like tone, speed, and gender.
    """
    
    def __init__(self, api_key: str, provider: IntegrationProvider):
        """
        Initialize the voice generator.
        
        Args:
            api_key: API key for the provider
            provider: Integration provider to use
        """
        self.api_key = api_key
        self.provider = provider
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(
        self,
        script: Dict[str, Any],
        template_config: Dict[str, Any],
    ) -> StepResult:
        """
        Generate voice-over audio for the script.
        
        Args:
            script: Script data from script generation step
            template_config: Template configuration
            
        Returns:
            StepResult with voice data
        """
        try:
            if self.provider == IntegrationProvider.ELEVENLABS:
                return await self._generate_elevenlabs(script, template_config)
            else:
                return StepResult(
                    success=False,
                    error=f"Unsupported voice provider: {self.provider.value}",
                )
        except Exception as e:
            logger.exception("Voice generation failed")
            return StepResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )
        finally:
            await self.client.aclose()
    
    async def _generate_elevenlabs(
        self,
        script: Dict[str, Any],
        template_config: Dict[str, Any],
    ) -> StepResult:
        """Generate voice using ElevenLabs."""
        
        # Get voice settings from template
        audio_config = template_config.get("audio", {})
        voice_gender = audio_config.get("voice_gender", "neutral")
        voice_tone = audio_config.get("voice_tone", "professional")
        voice_speed = audio_config.get("voice_speed", "normal")
        
        # Select voice ID
        voice_id = self._select_voice(voice_gender, voice_tone)
        
        # Get the full narration text
        script_data = script.get("script", script)
        narration_parts = []
        
        # Add hook
        if script_data.get("hook"):
            narration_parts.append(script_data["hook"])
        
        # Add scene narrations
        for scene in script_data.get("scenes", []):
            if scene.get("narration"):
                narration_parts.append(scene["narration"])
        
        # Add CTA
        if script_data.get("cta"):
            narration_parts.append(script_data["cta"])
        
        full_narration = " ".join(narration_parts)
        
        if not full_narration.strip():
            return StepResult(
                success=False,
                error="No narration text found in script",
            )
        
        # Generate audio
        response = await self.client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": full_narration,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": self._get_style_value(voice_tone),
                    "use_speaker_boost": True,
                },
            },
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
            return StepResult(
                success=False,
                error=f"ElevenLabs API error: {error_data}",
                error_details=error_data,
            )
        
        # Get audio data
        audio_data = response.content
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # Estimate duration (rough estimate based on text length)
        # Average speaking rate is about 150 words per minute
        word_count = len(full_narration.split())
        estimated_duration = (word_count / 150) * 60
        
        return StepResult(
            success=True,
            data={
                "audio_base64": audio_base64,
                "audio_format": "mp3",
                "voice_id": voice_id,
                "narration_text": full_narration,
                "estimated_duration": estimated_duration,
                "provider": self.provider.value,
            },
        )
    
    def _select_voice(self, gender: str, tone: str) -> str:
        """Select the appropriate voice ID."""
        gender_voices = ELEVENLABS_VOICES.get(gender, ELEVENLABS_VOICES["neutral"])
        return gender_voices.get(tone, gender_voices.get("professional"))
    
    def _get_style_value(self, tone: str) -> float:
        """Get the style value for a tone."""
        style_map = {
            "professional": 0.0,
            "casual": 0.3,
            "energetic": 0.7,
            "dramatic": 0.5,
            "friendly": 0.4,
            "serious": 0.1,
        }
        return style_map.get(tone, 0.0)

