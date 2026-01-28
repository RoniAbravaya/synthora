"""
Provider Implementations

This module contains the provider implementations for video generation.
Each provider handles a specific step in the video generation pipeline.

Categories:
- script: Script/text generation (OpenAI GPT, Anthropic)
- voice: Voice/TTS generation (OpenAI TTS, ElevenLabs, PlayHT)
- media: Stock media fetching (Pexels, Unsplash, Pixabay)
- video_ai: AI video generation (Sora, Runway, etc.)
- assembly: Video assembly (FFmpeg, Creatomate, Shotstack)
"""

from app.integrations.providers.base import (
    BaseProvider,
    ProviderResult,
    ProviderConfig,
    ProviderCapability,
    TimingSegment,
)
from app.integrations.providers.factory import (
    ProviderFactory,
    get_provider,
    get_providers_for_category,
)

__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderResult",
    "ProviderConfig",
    "ProviderCapability",
    "TimingSegment",
    
    # Factory
    "ProviderFactory",
    "get_provider",
    "get_providers_for_category",
]
