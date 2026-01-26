"""
Integration Service

Business logic for managing user API key integrations.
Handles encryption, validation, and integration status checks.
"""

import logging
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.integration import (
    Integration,
    IntegrationProvider,
    IntegrationCategory,
    PROVIDER_CATEGORIES,
)
from app.models.user import User
from app.core.security import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


# Required categories for video generation
# User must have at least one integration from each of these categories
REQUIRED_CATEGORIES = {
    IntegrationCategory.SCRIPT,    # OpenAI for script generation
    IntegrationCategory.VOICE,     # ElevenLabs for voice-over
    IntegrationCategory.MEDIA,     # Pexels/Unsplash for stock footage
    IntegrationCategory.ASSEMBLY,  # FFmpeg/Creatomate etc. for assembly
}

# Optional but recommended
OPTIONAL_CATEGORIES = {
    IntegrationCategory.VIDEO_AI,  # AI video generation (Runway, Sora, etc.)
}


class IntegrationService:
    """
    Service class for integration management operations.
    
    Handles:
    - CRUD operations for integrations
    - API key encryption/decryption
    - Validation status tracking
    - Minimum requirements checking
    """
    
    def __init__(self, db: Session):
        """
        Initialize the integration service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_by_id(self, integration_id: UUID) -> Optional[Integration]:
        """Get an integration by ID."""
        return self.db.query(Integration).filter(Integration.id == integration_id).first()
    
    def get_user_integrations(self, user_id: UUID) -> List[Integration]:
        """
        Get all integrations for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of Integration instances
        """
        return self.db.query(Integration).filter(
            Integration.user_id == user_id
        ).order_by(Integration.provider).all()
    
    def get_active_integrations(self, user_id: UUID) -> List[Integration]:
        """
        Get all active and validated integrations for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of active Integration instances
        """
        return self.db.query(Integration).filter(
            and_(
                Integration.user_id == user_id,
                Integration.is_active == True,
                Integration.is_valid == True,  # Use actual column name, not property
            )
        ).all()
    
    def get_by_provider(
        self,
        user_id: UUID,
        provider: IntegrationProvider
    ) -> Optional[Integration]:
        """
        Get a specific integration by provider.
        
        Args:
            user_id: User's UUID
            provider: Integration provider
            
        Returns:
            Integration instance or None
        """
        return self.db.query(Integration).filter(
            and_(
                Integration.user_id == user_id,
                Integration.provider == provider,
            )
        ).first()
    
    def get_by_category(
        self,
        user_id: UUID,
        category: IntegrationCategory
    ) -> List[Integration]:
        """
        Get all integrations in a category for a user.
        
        Args:
            user_id: User's UUID
            category: Integration category
            
        Returns:
            List of Integration instances in that category
        """
        # Get providers in this category
        providers_in_category = [
            provider for provider, cat in PROVIDER_CATEGORIES.items()
            if cat == category
        ]
        
        return self.db.query(Integration).filter(
            and_(
                Integration.user_id == user_id,
                Integration.provider.in_(providers_in_category),
            )
        ).all()
    
    # =========================================================================
    # Create/Update Methods
    # =========================================================================
    
    def add_integration(
        self,
        user_id: UUID,
        provider: IntegrationProvider,
        api_key: str,
    ) -> Integration:
        """
        Add a new integration for a user.
        
        Args:
            user_id: User's UUID
            provider: Integration provider
            api_key: Plain text API key (will be encrypted)
            
        Returns:
            Newly created Integration instance
            
        Raises:
            ValueError: If integration already exists for this provider
        """
        # Check if integration already exists
        existing = self.get_by_provider(user_id, provider)
        if existing:
            raise ValueError(f"Integration for {provider.value} already exists. Use update instead.")
        
        # Encrypt the API key
        encrypted_key = encrypt_value(api_key)
        
        integration = Integration(
            user_id=user_id,
            provider=provider,
            api_key_encrypted=encrypted_key,
            is_active=True,
            is_valid=False,  # Will be validated separately
        )
        
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        
        logger.info(f"Added integration for user {user_id}: {provider.value}")
        return integration
    
    def update_api_key(
        self,
        integration: Integration,
        new_api_key: str,
    ) -> Integration:
        """
        Update an integration's API key.
        
        Args:
            integration: Integration instance to update
            new_api_key: New plain text API key
            
        Returns:
            Updated Integration instance
        """
        # Encrypt the new API key
        integration.api_key_encrypted = encrypt_value(new_api_key)
        integration.is_valid = False  # Needs re-validation
        integration.last_validated_at = None
        integration.validation_error = None
        
        self.db.commit()
        self.db.refresh(integration)
        
        logger.info(f"Updated API key for integration {integration.id}")
        return integration
    
    def set_validation_status(
        self,
        integration: Integration,
        is_valid: bool,
        error_message: Optional[str] = None,
    ) -> Integration:
        """
        Update the validation status of an integration.
        
        Args:
            integration: Integration instance
            is_valid: Whether validation passed
            error_message: Error message if validation failed
            
        Returns:
            Updated Integration instance
        """
        integration.is_valid = is_valid
        integration.last_validated_at = datetime.utcnow()
        integration.validation_error = error_message if not is_valid else None
        
        self.db.commit()
        self.db.refresh(integration)
        
        status = "valid" if is_valid else "invalid"
        logger.info(f"Integration {integration.id} marked as {status}")
        return integration
    
    def set_active_status(
        self,
        integration: Integration,
        is_active: bool,
    ) -> Integration:
        """
        Enable or disable an integration.
        
        Args:
            integration: Integration instance
            is_active: New active status
            
        Returns:
            Updated Integration instance
        """
        integration.is_active = is_active
        
        self.db.commit()
        self.db.refresh(integration)
        
        status = "enabled" if is_active else "disabled"
        logger.info(f"Integration {integration.id} {status}")
        return integration
    
    def delete_integration(self, integration: Integration) -> None:
        """
        Delete an integration.
        
        Args:
            integration: Integration instance to delete
        """
        integration_id = integration.id
        provider = integration.provider
        
        self.db.delete(integration)
        self.db.commit()
        
        logger.info(f"Deleted integration {integration_id} ({provider.value})")
    
    def mark_used(self, integration: Integration) -> None:
        """
        Update the last_used_at timestamp.
        
        Args:
            integration: Integration instance
        """
        integration.last_used_at = datetime.utcnow()
        self.db.commit()
    
    # =========================================================================
    # Decryption Methods
    # =========================================================================
    
    def get_decrypted_api_key(self, integration: Integration) -> str:
        """
        Get the decrypted API key for an integration.
        
        Args:
            integration: Integration instance
            
        Returns:
            Decrypted API key
            
        Raises:
            ValueError: If no API key is stored
        """
        if not integration.api_key_encrypted:
            raise ValueError("No API key stored for this integration")
        
        return decrypt_value(integration.api_key_encrypted)
    
    def get_masked_api_key(self, integration: Integration) -> str:
        """
        Get a masked version of the API key (last 4 characters visible).
        
        Args:
            integration: Integration instance
            
        Returns:
            Masked API key string (e.g., "sk-...xxxx")
        """
        if not integration.api_key_encrypted:
            return "Not configured"
        
        try:
            api_key = self.get_decrypted_api_key(integration)
            if len(api_key) <= 4:
                return "****"
            # Limit to 50 chars max to fit database column
            visible_chars = api_key[-4:]
            mask_len = min(len(api_key) - 4, 46)  # 46 asterisks + 4 visible = 50 max
            return f"{'*' * mask_len}{visible_chars}"
        except Exception:
            return "Error decrypting"
    
    # =========================================================================
    # Requirements Checking
    # =========================================================================
    
    def get_configured_categories(self, user_id: UUID) -> Set[IntegrationCategory]:
        """
        Get the set of categories the user has configured.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Set of configured IntegrationCategory values
        """
        integrations = self.get_active_integrations(user_id)
        
        categories = set()
        for integration in integrations:
            category = PROVIDER_CATEGORIES.get(integration.provider)
            if category:
                categories.add(category)
        
        return categories
    
    def get_missing_categories(self, user_id: UUID) -> Set[IntegrationCategory]:
        """
        Get the required categories the user hasn't configured.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Set of missing IntegrationCategory values
        """
        configured = self.get_configured_categories(user_id)
        return REQUIRED_CATEGORIES - configured
    
    def can_generate_videos(self, user_id: UUID) -> bool:
        """
        Check if user has enough integrations to generate videos.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if user can generate videos
        """
        missing = self.get_missing_categories(user_id)
        return len(missing) == 0
    
    def check_minimum_integrations(self, user_id: UUID) -> tuple[bool, List[str]]:
        """
        Check if user has the minimum required integrations for video generation.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Tuple of (has_required: bool, missing_categories: list of category names)
        """
        missing = self.get_missing_categories(user_id)
        missing_names = [cat.value for cat in missing]
        has_required = len(missing) == 0
        return has_required, missing_names
    
    def get_integration_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive integration status for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with integration status details
        """
        integrations = self.get_user_integrations(user_id)
        configured = self.get_configured_categories(user_id)
        missing = self.get_missing_categories(user_id)
        
        return {
            "total_configured": len(integrations),
            "active_count": sum(1 for i in integrations if i.is_active and i.is_valid),
            "configured_categories": [c.value for c in configured],
            "missing_categories": [c.value for c in missing],
            "can_generate_videos": len(missing) == 0,
            "minimum_required": len(REQUIRED_CATEGORIES),
        }
    
    # =========================================================================
    # Provider Information
    # =========================================================================
    
    @staticmethod
    def get_provider_info(provider: IntegrationProvider) -> Dict[str, Any]:
        """
        Get information about a provider.
        
        Args:
            provider: Integration provider
            
        Returns:
            Dictionary with provider details
        """
        # Provider display names
        display_names = {
            IntegrationProvider.OPENAI: "OpenAI (ChatGPT)",
            IntegrationProvider.ELEVENLABS: "ElevenLabs",
            IntegrationProvider.PEXELS: "Pexels",
            IntegrationProvider.UNSPLASH: "Unsplash",
            IntegrationProvider.RUNWAY: "Runway Gen-4",
            IntegrationProvider.SORA: "OpenAI Sora",
            IntegrationProvider.VEO: "Google Veo 3",
            IntegrationProvider.LUMA: "Luma Dream Machine",
            IntegrationProvider.IMAGINEART: "ImagineArt AI",
            IntegrationProvider.PIXVERSE: "PixVerse",
            IntegrationProvider.SEEDANCE: "Seedance AI",
            IntegrationProvider.WAN: "Wan2.6",
            IntegrationProvider.HAILUO: "Hailuo AI",
            IntegrationProvider.LTX: "LTX-2",
            IntegrationProvider.FFMPEG: "FFmpeg (Local)",
            IntegrationProvider.CREATOMATE: "Creatomate",
            IntegrationProvider.SHOTSTACK: "Shotstack",
            IntegrationProvider.REMOTION: "Remotion",
            IntegrationProvider.EDITFRAME: "Editframe",
        }
        
        # Documentation URLs
        docs_urls = {
            IntegrationProvider.OPENAI: "https://platform.openai.com/api-keys",
            IntegrationProvider.ELEVENLABS: "https://elevenlabs.io/api",
            IntegrationProvider.PEXELS: "https://www.pexels.com/api/",
            IntegrationProvider.UNSPLASH: "https://unsplash.com/developers",
            IntegrationProvider.RUNWAY: "https://runwayml.com/api",
            IntegrationProvider.SORA: "https://openai.com/sora",
            IntegrationProvider.VEO: "https://cloud.google.com/video-intelligence",
            IntegrationProvider.LUMA: "https://lumalabs.ai/dream-machine",
            IntegrationProvider.IMAGINEART: "https://www.imagine.art/api",
            IntegrationProvider.PIXVERSE: "https://pixverse.ai",
            IntegrationProvider.SEEDANCE: "https://seedance.ai",
            IntegrationProvider.WAN: "https://wan.video",
            IntegrationProvider.HAILUO: "https://hailuoai.com",
            IntegrationProvider.LTX: "https://ltx.studio",
            IntegrationProvider.FFMPEG: "https://ffmpeg.org/documentation.html",
            IntegrationProvider.CREATOMATE: "https://creatomate.com/docs",
            IntegrationProvider.SHOTSTACK: "https://shotstack.io/docs",
            IntegrationProvider.REMOTION: "https://www.remotion.dev/docs",
            IntegrationProvider.EDITFRAME: "https://docs.editframe.com",
        }
        
        # Auth methods
        auth_methods = {
            IntegrationProvider.FFMPEG: "none",  # Local binary
        }
        
        category = PROVIDER_CATEGORIES.get(provider)
        
        return {
            "provider": provider.value,
            "name": display_names.get(provider, provider.value),
            "category": category.value if category else "unknown",
            "auth_method": auth_methods.get(provider, "api_key"),
            "docs_url": docs_urls.get(provider),
            "required": category in REQUIRED_CATEGORIES if category else False,
        }
    
    @staticmethod
    def get_all_providers_info() -> List[Dict[str, Any]]:
        """
        Get information about all available providers.
        
        Returns:
            List of provider info dictionaries
        """
        return [
            IntegrationService.get_provider_info(provider)
            for provider in IntegrationProvider
        ]
    
    @staticmethod
    def get_providers_by_category() -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all providers grouped by category.
        
        Returns:
            Dictionary mapping category names to lists of provider info
        """
        result = {}
        
        for category in IntegrationCategory:
            providers = [
                IntegrationService.get_provider_info(provider)
                for provider, cat in PROVIDER_CATEGORIES.items()
                if cat == category
            ]
            result[category.value] = providers
        
        return result


def get_integration_service(db: Session) -> IntegrationService:
    """Factory function to create an IntegrationService instance."""
    return IntegrationService(db)

