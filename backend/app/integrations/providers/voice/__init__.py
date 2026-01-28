"""Voice/TTS generation providers."""

from app.integrations.providers.voice.elevenlabs import ElevenLabsProvider
from app.integrations.providers.voice.openai_tts import OpenAITTSProvider

__all__ = ["ElevenLabsProvider", "OpenAITTSProvider"]
