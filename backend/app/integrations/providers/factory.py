"""
Provider Factory

Creates provider instances based on provider name and category.
Handles provider registration and lookup.
"""

import logging
from typing import Optional, Dict, Type, List, TYPE_CHECKING

from app.models.integration import (
    IntegrationProvider,
    IntegrationCategory,
    PROVIDER_CATEGORIES,
    PROVIDER_PRICING,
    PROVIDER_INFO,
)
from app.integrations.providers.base import (
    BaseProvider,
    ScriptProvider,
    VoiceProvider,
    MediaProvider,
    VideoAIProvider,
    AssemblyProvider,
    ProviderConfig,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Provider Registry
# =============================================================================

# Maps provider names to their implementation classes
# Will be populated as provider implementations are added
_PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {}


def register_provider(provider_name: str, provider_class: Type[BaseProvider]) -> None:
    """
    Register a provider implementation.
    
    Args:
        provider_name: Provider identifier (e.g., 'openai_gpt')
        provider_class: Provider class to register
    """
    _PROVIDER_REGISTRY[provider_name] = provider_class
    logger.debug(f"Registered provider: {provider_name}")


def get_registered_providers() -> List[str]:
    """Get list of registered provider names."""
    return list(_PROVIDER_REGISTRY.keys())


# =============================================================================
# Provider Factory
# =============================================================================

class ProviderFactory:
    """
    Factory for creating provider instances.
    
    Usage:
        factory = ProviderFactory(db_session)
        provider = factory.get_provider('openai_gpt', api_key)
        result = await provider.execute(input_data)
    """
    
    def __init__(self, db: Optional["Session"] = None):
        """
        Initialize the factory.
        
        Args:
            db: Optional database session for logging
        """
        self.db = db
    
    def get_provider(
        self,
        provider_name: str,
        api_key: str,
        config: Optional[ProviderConfig] = None,
    ) -> Optional[BaseProvider]:
        """
        Get a provider instance.
        
        Args:
            provider_name: Provider identifier
            api_key: API key for authentication
            config: Optional provider configuration
            
        Returns:
            Provider instance, or None if provider not found
        """
        provider_class = _PROVIDER_REGISTRY.get(provider_name)
        
        if provider_class is None:
            logger.warning(f"Provider not found: {provider_name}")
            return None
        
        return provider_class(
            api_key=api_key,
            db=self.db,
            config=config,
        )
    
    def get_providers_for_category(
        self,
        category: IntegrationCategory,
    ) -> List[str]:
        """
        Get all registered providers for a category.
        
        Args:
            category: Provider category
            
        Returns:
            List of provider names
        """
        result = []
        
        for provider_name, provider_class in _PROVIDER_REGISTRY.items():
            if provider_class.category == category.value:
                result.append(provider_name)
        
        return result
    
    @staticmethod
    def get_provider_info(provider_name: str) -> Dict:
        """
        Get information about a provider.
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            Dictionary with provider info
        """
        info = PROVIDER_INFO.get(provider_name, {})
        pricing = PROVIDER_PRICING.get(provider_name, {})
        
        # Get category from enum mapping
        category = None
        try:
            provider_enum = IntegrationProvider(provider_name)
            category = PROVIDER_CATEGORIES.get(provider_enum)
        except ValueError:
            pass
        
        return {
            "name": provider_name,
            "display_name": info.get("display_name", provider_name),
            "description": info.get("description", ""),
            "docs_url": info.get("docs_url", ""),
            "category": category.value if category else None,
            "estimated_cost": pricing.get("estimated_per_video", 0.0),
            "is_registered": provider_name in _PROVIDER_REGISTRY,
        }
    
    @staticmethod
    def get_all_providers_info() -> List[Dict]:
        """
        Get information about all available providers.
        
        Returns:
            List of provider info dictionaries
        """
        providers = []
        
        for provider in IntegrationProvider:
            info = ProviderFactory.get_provider_info(provider.value)
            providers.append(info)
        
        return providers


# =============================================================================
# Convenience Functions
# =============================================================================

def get_provider(
    provider_name: str,
    api_key: str,
    db: Optional["Session"] = None,
    config: Optional[ProviderConfig] = None,
) -> Optional[BaseProvider]:
    """
    Convenience function to get a provider instance.
    
    Args:
        provider_name: Provider identifier
        api_key: API key for authentication
        db: Optional database session
        config: Optional provider configuration
        
    Returns:
        Provider instance, or None if not found
    """
    factory = ProviderFactory(db)
    return factory.get_provider(provider_name, api_key, config)


def get_providers_for_category(
    category: IntegrationCategory,
    db: Optional["Session"] = None,
) -> List[str]:
    """
    Convenience function to get providers for a category.
    
    Args:
        category: Provider category
        db: Optional database session
        
    Returns:
        List of provider names
    """
    factory = ProviderFactory(db)
    return factory.get_providers_for_category(category)


# =============================================================================
# Import and Register Provider Implementations
# =============================================================================

def _register_providers():
    """
    Register all provider implementations.
    
    This is called at module load time to register all available providers.
    Add imports here as provider implementations are created.
    """
    # Script providers
    try:
        from app.integrations.providers.script.openai_gpt import OpenAIGPTProvider
        register_provider("openai_gpt", OpenAIGPTProvider)
    except ImportError:
        logger.debug("OpenAI GPT provider not available")
    
    try:
        from app.integrations.providers.script.anthropic import AnthropicProvider
        register_provider("anthropic", AnthropicProvider)
    except ImportError:
        logger.debug("Anthropic provider not available")
    
    # Voice providers
    try:
        from app.integrations.providers.voice.openai_tts import OpenAITTSProvider
        register_provider("openai_tts", OpenAITTSProvider)
    except ImportError:
        logger.debug("OpenAI TTS provider not available")
    
    try:
        from app.integrations.providers.voice.elevenlabs import ElevenLabsProvider
        register_provider("elevenlabs", ElevenLabsProvider)
    except ImportError:
        logger.debug("ElevenLabs provider not available")
    
    try:
        from app.integrations.providers.voice.playht import PlayHTProvider
        register_provider("playht", PlayHTProvider)
    except ImportError:
        logger.debug("PlayHT provider not available")
    
    # Media providers
    try:
        from app.integrations.providers.media.pexels import PexelsProvider
        register_provider("pexels", PexelsProvider)
    except ImportError:
        logger.debug("Pexels provider not available")
    
    try:
        from app.integrations.providers.media.unsplash import UnsplashProvider
        register_provider("unsplash", UnsplashProvider)
    except ImportError:
        logger.debug("Unsplash provider not available")
    
    try:
        from app.integrations.providers.media.pixabay import PixabayProvider
        register_provider("pixabay", PixabayProvider)
    except ImportError:
        logger.debug("Pixabay provider not available")
    
    # Video AI providers
    try:
        from app.integrations.providers.video_ai.openai_sora import OpenAISoraProvider
        register_provider("openai_sora", OpenAISoraProvider)
    except ImportError:
        logger.debug("OpenAI Sora provider not available")
    
    try:
        from app.integrations.providers.video_ai.runway import RunwayProvider
        register_provider("runway", RunwayProvider)
    except ImportError:
        logger.debug("Runway provider not available")
    
    try:
        from app.integrations.providers.video_ai.luma import LumaProvider
        register_provider("luma", LumaProvider)
    except ImportError:
        logger.debug("Luma provider not available")
    
    # Assembly providers
    try:
        from app.integrations.providers.assembly.ffmpeg import FFmpegProvider
        register_provider("ffmpeg", FFmpegProvider)
    except ImportError:
        logger.debug("FFmpeg provider not available")
    
    try:
        from app.integrations.providers.assembly.creatomate import CreatomateProvider
        register_provider("creatomate", CreatomateProvider)
    except ImportError:
        logger.debug("Creatomate provider not available")
    
    try:
        from app.integrations.providers.assembly.shotstack import ShotstackProvider
        register_provider("shotstack", ShotstackProvider)
    except ImportError:
        logger.debug("Shotstack provider not available")


# Register providers on module import
_register_providers()
