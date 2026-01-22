"""
Integration Validator Factory

Provides factory functions to get the appropriate validator for a provider.
"""

import logging
from typing import Optional, Type

from app.models.integration import IntegrationProvider
from app.integrations.base import BaseValidator, ValidationResult
from app.integrations.validators import (
    OpenAIValidator,
    AnthropicValidator,
    ElevenLabsValidator,
    PlayHTValidator,
    PexelsValidator,
    UnsplashValidator,
    PixabayValidator,
    RunwayValidator,
    HeyGenValidator,
    SoraValidator,
    VeoValidator,
    LumaValidator,
    ImagineArtValidator,
    PixVerseValidator,
    SeedanceValidator,
    WanValidator,
    HailuoValidator,
    LTXValidator,
    FFmpegValidator,
    CreatomateValidator,
    ShotstackValidator,
    RemotionValidator,
    EditframeValidator,
)

logger = logging.getLogger(__name__)


# Mapping of providers to their validator classes
VALIDATOR_MAP: dict[IntegrationProvider, Type[BaseValidator]] = {
    # Script/Text AI
    IntegrationProvider.OPENAI: OpenAIValidator,
    IntegrationProvider.ANTHROPIC: AnthropicValidator,
    
    # Voice AI
    IntegrationProvider.ELEVENLABS: ElevenLabsValidator,
    IntegrationProvider.PLAYHT: PlayHTValidator,
    
    # Stock Media
    IntegrationProvider.PEXELS: PexelsValidator,
    IntegrationProvider.UNSPLASH: UnsplashValidator,
    IntegrationProvider.PIXABAY: PixabayValidator,
    
    # Video AI
    IntegrationProvider.RUNWAY: RunwayValidator,
    IntegrationProvider.HEYGEN: HeyGenValidator,
    IntegrationProvider.SORA: SoraValidator,
    IntegrationProvider.VEO: VeoValidator,
    IntegrationProvider.LUMA: LumaValidator,
    IntegrationProvider.IMAGINEART: ImagineArtValidator,
    IntegrationProvider.PIXVERSE: PixVerseValidator,
    IntegrationProvider.SEEDANCE: SeedanceValidator,
    IntegrationProvider.WAN: WanValidator,
    IntegrationProvider.HAILUO: HailuoValidator,
    IntegrationProvider.LTX: LTXValidator,
    
    # Video Assembly
    IntegrationProvider.FFMPEG: FFmpegValidator,
    IntegrationProvider.CREATOMATE: CreatomateValidator,
    IntegrationProvider.SHOTSTACK: ShotstackValidator,
    IntegrationProvider.REMOTION: RemotionValidator,
    IntegrationProvider.EDITFRAME: EditframeValidator,
}


def get_validator(
    provider: IntegrationProvider,
    api_key: str
) -> Optional[BaseValidator]:
    """
    Get the appropriate validator for a provider.
    
    Args:
        provider: The integration provider
        api_key: The API key to validate
        
    Returns:
        Validator instance, or None if no validator exists for the provider
    """
    validator_class = VALIDATOR_MAP.get(provider)
    
    if validator_class is None:
        logger.warning(f"No validator found for provider: {provider.value}")
        return None
    
    return validator_class(api_key)


async def validate_integration(
    provider: IntegrationProvider,
    api_key: str
) -> ValidationResult:
    """
    Validate an API key for a provider.
    
    This is a convenience function that creates a validator,
    runs validation, and cleans up resources.
    
    Args:
        provider: The integration provider
        api_key: The API key to validate
        
    Returns:
        ValidationResult with validation status and details
    """
    validator = get_validator(provider, api_key)
    
    if validator is None:
        return ValidationResult(
            valid=False,
            message=f"No validator available for {provider.value}",
            error_code="no_validator",
        )
    
    try:
        async with validator:
            result = await validator.validate()
            logger.info(
                f"Validation result for {provider.value}: "
                f"{'valid' if result.valid else 'invalid'}"
            )
            return result
    except Exception as e:
        logger.error(f"Validation error for {provider.value}: {e}")
        return ValidationResult(
            valid=False,
            message=f"Validation failed: {str(e)}",
            error_code="validation_error",
        )


def get_supported_providers() -> list[str]:
    """
    Get a list of providers with validators.
    
    Returns:
        List of provider names that have validators
    """
    return [provider.value for provider in VALIDATOR_MAP.keys()]


def has_validator(provider: IntegrationProvider) -> bool:
    """
    Check if a provider has a validator.
    
    Args:
        provider: The integration provider
        
    Returns:
        True if a validator exists for the provider
    """
    return provider in VALIDATOR_MAP

