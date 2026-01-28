"""
User Generation Settings Service

Manages user preferences for video generation:
- Default provider selection for each category
- Subtitle style preferences
- Cost estimation based on selected providers
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_generation_settings import (
    UserGenerationSettings,
    SubtitleStyle,
    SUBTITLE_STYLE_CONFIGS,
)
from app.models.integration import (
    Integration,
    IntegrationCategory,
    PROVIDER_CATEGORIES,
    PROVIDER_PRICING,
    IntegrationProvider,
    get_providers_for_category,
)

logger = logging.getLogger(__name__)


class UserGenerationSettingsService:
    """
    Service for managing user generation settings.
    
    Provides methods to:
    - Get or create user settings
    - Update settings
    - Get effective providers (user defaults or first available)
    - Calculate cost estimates
    """
    
    def __init__(self, db: Session):
        """
        Initialize the service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_settings(self, user_id: UUID) -> UserGenerationSettings:
        """
        Get user's generation settings, creating defaults if not exists.
        
        Args:
            user_id: User ID
            
        Returns:
            UserGenerationSettings instance
        """
        settings = self.db.query(UserGenerationSettings).filter(
            UserGenerationSettings.user_id == user_id
        ).first()
        
        if settings is None:
            # Create default settings
            settings = UserGenerationSettings(
                user_id=user_id,
                subtitle_style=SubtitleStyle.DEFAULT,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
            logger.info(f"Created default generation settings for user {user_id}")
        
        return settings
    
    def update_settings(
        self,
        user_id: UUID,
        updates: Dict[str, Any],
    ) -> UserGenerationSettings:
        """
        Update user's generation settings.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated UserGenerationSettings instance
        """
        settings = self.get_settings(user_id)
        
        # Validate and apply updates
        allowed_fields = {
            "default_script_provider",
            "default_voice_provider",
            "default_media_provider",
            "default_video_ai_provider",
            "default_assembly_provider",
            "subtitle_style",
        }
        
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            
            # Validate subtitle style
            if field == "subtitle_style" and value not in SubtitleStyle.ALL:
                raise ValueError(f"Invalid subtitle style: {value}")
            
            # Validate provider exists for category
            if field.startswith("default_") and field.endswith("_provider") and value:
                category_name = field.replace("default_", "").replace("_provider", "")
                if not self._validate_provider_for_category(user_id, value, category_name):
                    raise ValueError(f"Provider {value} is not enabled for {category_name}")
            
            setattr(settings, field, value)
        
        settings.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(settings)
        
        logger.info(f"Updated generation settings for user {user_id}")
        return settings
    
    def _validate_provider_for_category(
        self,
        user_id: UUID,
        provider: str,
        category: str,
    ) -> bool:
        """
        Validate that a provider belongs to the expected category
        and is enabled for the user.
        
        Args:
            user_id: User ID
            provider: Provider name
            category: Expected category name
            
        Returns:
            True if valid
        """
        # Check provider belongs to category
        try:
            provider_enum = IntegrationProvider(provider)
            provider_category = PROVIDER_CATEGORIES.get(provider_enum)
            
            if provider_category is None or provider_category.value != category:
                return False
        except ValueError:
            return False
        
        # Check user has this integration enabled
        integration = self.db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.provider == provider,
            Integration.is_active == True,
        ).first()
        
        return integration is not None
    
    def get_effective_providers(
        self,
        user_id: UUID,
    ) -> Dict[str, Optional[str]]:
        """
        Get the effective provider for each category.
        
        Returns user's default if set and valid, otherwise
        returns the first available provider for that category.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping category to provider name
        """
        settings = self.get_settings(user_id)
        
        # Get user's enabled integrations grouped by category
        integrations = self.db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.is_active == True,
        ).all()
        
        # Group by category
        integrations_by_category: Dict[str, List[str]] = {}
        for integration in integrations:
            category = integration.category
            if category not in integrations_by_category:
                integrations_by_category[category] = []
            integrations_by_category[category].append(integration.provider)
        
        # Determine effective provider for each category
        result = {}
        
        for category in IntegrationCategory:
            category_name = category.value
            available = integrations_by_category.get(category_name, [])
            
            # Get user's default
            default = settings.get_default_provider(category_name)
            
            # Use default if set and available, otherwise first available
            if default and default in available:
                result[category_name] = default
            elif available:
                result[category_name] = available[0]
            else:
                result[category_name] = None
        
        return result
    
    def get_available_providers(
        self,
        user_id: UUID,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available providers for each category based on user's integrations.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping category to list of provider info
        """
        # Get user's enabled integrations
        integrations = self.db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.is_active == True,
        ).all()
        
        # Group by category with provider info
        result: Dict[str, List[Dict[str, Any]]] = {}
        
        for category in IntegrationCategory:
            result[category.value] = []
        
        for integration in integrations:
            category = integration.category
            pricing = PROVIDER_PRICING.get(integration.provider, {})
            
            result[category].append({
                "provider": integration.provider,
                "display_name": integration.display_name,
                "is_valid": integration.is_valid,
                "estimated_cost": pricing.get("estimated_per_video", 0.0),
            })
        
        return result
    
    def calculate_cost_estimate(
        self,
        user_id: UUID,
        providers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate estimated cost per video based on selected providers.
        
        Args:
            user_id: User ID
            providers: Optional custom provider selection (uses effective if not provided)
            
        Returns:
            Cost breakdown dictionary
        """
        if providers is None:
            providers = self.get_effective_providers(user_id)
        
        breakdown = {}
        total = 0.0
        
        for category, provider in providers.items():
            if provider:
                pricing = PROVIDER_PRICING.get(provider, {})
                cost = pricing.get("estimated_per_video", 0.0)
                breakdown[category] = {
                    "provider": provider,
                    "display_name": pricing.get("name", provider),
                    "cost": cost,
                }
                total += cost
            else:
                breakdown[category] = {
                    "provider": None,
                    "display_name": "Not configured",
                    "cost": 0.0,
                }
        
        return {
            "breakdown": breakdown,
            "total_estimated_cost": round(total, 2),
            "currency": "USD",
            "note": "Estimated cost per ~30 second video with ~5 scenes",
        }
    
    def get_subtitle_config(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get the subtitle style configuration for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Subtitle style configuration dictionary
        """
        settings = self.get_settings(user_id)
        return settings.subtitle_config
    
    def get_subtitle_styles(self) -> List[Dict[str, Any]]:
        """
        Get all available subtitle styles with their configurations.
        
        Returns:
            List of subtitle style info
        """
        styles = []
        
        for style_name in SubtitleStyle.ALL:
            config = SUBTITLE_STYLE_CONFIGS.get(style_name, {})
            styles.append({
                "name": style_name,
                "display_name": style_name.title(),
                "description": self._get_style_description(style_name),
                "is_default": style_name == SubtitleStyle.DEFAULT,
                "preview": {
                    "font": config.get("font_name", "Arial"),
                    "color": self._convert_ass_color(config.get("primary_color", "&HFFFFFF")),
                    "has_background": config.get("background_color") is not None,
                },
            })
        
        return styles
    
    def _get_style_description(self, style: str) -> str:
        """Get description for a subtitle style."""
        descriptions = {
            SubtitleStyle.CLASSIC: "White text with black outline, positioned at bottom",
            SubtitleStyle.MODERN: "Clean white text with semi-transparent background",
            SubtitleStyle.BOLD: "Bold yellow text centered on screen",
            SubtitleStyle.MINIMAL: "Subtle white text with dark background",
        }
        return descriptions.get(style, "")
    
    def _convert_ass_color(self, ass_color: str) -> str:
        """Convert ASS color format to CSS hex color."""
        if not ass_color or not ass_color.startswith("&H"):
            return "#FFFFFF"
        
        # ASS format is &HBBGGRR (with optional alpha)
        hex_part = ass_color[2:].lstrip("H")
        
        # Handle different lengths
        if len(hex_part) == 6:
            # BBGGRR
            bb, gg, rr = hex_part[0:2], hex_part[2:4], hex_part[4:6]
            return f"#{rr}{gg}{bb}"
        elif len(hex_part) == 8:
            # AABBGGRR
            bb, gg, rr = hex_part[2:4], hex_part[4:6], hex_part[6:8]
            return f"#{rr}{gg}{bb}"
        
        return "#FFFFFF"
