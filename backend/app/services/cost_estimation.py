"""
Cost Estimation Service

Calculates estimated costs for video generation based on selected providers.
Uses hardcoded pricing data that should be updated periodically.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.integration import (
    IntegrationCategory,
    PROVIDER_PRICING,
    PROVIDER_INFO,
)
from app.services.user_generation_settings import UserGenerationSettingsService

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdownItem:
    """Cost breakdown for a single category."""
    category: str
    provider: Optional[str]
    provider_name: str
    cost: float
    unit: str
    description: str


@dataclass
class CostEstimate:
    """Complete cost estimate for video generation."""
    breakdown: List[CostBreakdownItem]
    total_cost: float
    currency: str
    assumptions: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "breakdown": [
                {
                    "category": item.category,
                    "provider": item.provider,
                    "provider_name": item.provider_name,
                    "cost": item.cost,
                    "unit": item.unit,
                    "description": item.description,
                }
                for item in self.breakdown
            ],
            "total_cost": self.total_cost,
            "currency": self.currency,
            "assumptions": self.assumptions,
        }


class CostEstimationService:
    """
    Service for estimating video generation costs.
    
    Provides:
    - Cost estimation based on selected providers
    - Provider pricing information
    - Cost comparison between providers
    
    Pricing data is hardcoded and based on typical usage:
    - ~30 second video
    - ~5 scenes
    - ~500 characters of narration
    
    Note: Prices should be reviewed and updated quarterly.
    """
    
    # Default assumptions for cost estimation
    DEFAULT_ASSUMPTIONS = "Based on typical 30-second video with 5 scenes"
    
    # Default currency
    CURRENCY = "USD"
    
    def __init__(self, db: Session):
        """
        Initialize the service.
        
        Args:
            db: Database session
        """
        self.db = db
        self._settings_service = UserGenerationSettingsService(db)
    
    def get_provider_cost(self, provider: str) -> float:
        """
        Get the estimated cost for a single provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Estimated cost per video in USD
        """
        pricing = PROVIDER_PRICING.get(provider, {})
        return pricing.get("estimated_per_video", 0.0)
    
    def get_provider_pricing_info(self, provider: str) -> Dict[str, Any]:
        """
        Get full pricing information for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Pricing information dictionary
        """
        pricing = PROVIDER_PRICING.get(provider, {})
        info = PROVIDER_INFO.get(provider, {})
        
        return {
            "provider": provider,
            "name": pricing.get("name", info.get("display_name", provider)),
            "unit": pricing.get("unit", "unknown"),
            "cost_per_unit": pricing.get("cost") or pricing.get("input_cost", 0),
            "estimated_per_video": pricing.get("estimated_per_video", 0.0),
            "description": pricing.get("description", info.get("description", "")),
        }
    
    def estimate_cost(
        self,
        providers: Dict[str, Optional[str]],
    ) -> CostEstimate:
        """
        Estimate total cost based on provider selection.
        
        Args:
            providers: Dictionary mapping category to provider name
            
        Returns:
            CostEstimate with breakdown and total
        """
        breakdown = []
        total = 0.0
        
        categories = [
            ("script", "Script Generation"),
            ("voice", "Voice Generation"),
            ("media", "Stock Media"),
            ("video_ai", "AI Video Generation"),
            ("assembly", "Video Assembly"),
        ]
        
        for category, display_name in categories:
            provider = providers.get(category)
            
            if provider:
                pricing = PROVIDER_PRICING.get(provider, {})
                cost = pricing.get("estimated_per_video", 0.0)
                
                breakdown.append(CostBreakdownItem(
                    category=category,
                    provider=provider,
                    provider_name=pricing.get("name", provider),
                    cost=cost,
                    unit=pricing.get("unit", "per video"),
                    description=pricing.get("description", ""),
                ))
                total += cost
            else:
                breakdown.append(CostBreakdownItem(
                    category=category,
                    provider=None,
                    provider_name="Not configured",
                    cost=0.0,
                    unit="N/A",
                    description=f"No {display_name.lower()} provider selected",
                ))
        
        return CostEstimate(
            breakdown=breakdown,
            total_cost=round(total, 2),
            currency=self.CURRENCY,
            assumptions=self.DEFAULT_ASSUMPTIONS,
        )
    
    def estimate_cost_for_user(self, user_id: UUID) -> CostEstimate:
        """
        Estimate cost for a user based on their default providers.
        
        Args:
            user_id: User ID
            
        Returns:
            CostEstimate based on user's effective providers
        """
        providers = self._settings_service.get_effective_providers(user_id)
        return self.estimate_cost(providers)
    
    def compare_providers(
        self,
        category: str,
    ) -> List[Dict[str, Any]]:
        """
        Compare costs between providers in a category.
        
        Args:
            category: Category to compare (script, voice, media, video_ai, assembly)
            
        Returns:
            List of providers with pricing info, sorted by cost
        """
        providers = []
        
        for provider_name, pricing in PROVIDER_PRICING.items():
            # Check if provider belongs to this category
            info = PROVIDER_INFO.get(provider_name, {})
            
            # Get category from IntegrationProvider enum
            from app.models.integration import IntegrationProvider, PROVIDER_CATEGORIES
            
            try:
                provider_enum = IntegrationProvider(provider_name)
                provider_category = PROVIDER_CATEGORIES.get(provider_enum)
                
                if provider_category and provider_category.value == category:
                    providers.append({
                        "provider": provider_name,
                        "name": pricing.get("name", info.get("display_name", provider_name)),
                        "cost": pricing.get("estimated_per_video", 0.0),
                        "unit": pricing.get("unit", "per video"),
                        "description": pricing.get("description", ""),
                    })
            except ValueError:
                continue
        
        # Sort by cost (ascending)
        providers.sort(key=lambda x: x["cost"])
        
        return providers
    
    def get_cheapest_combination(self) -> CostEstimate:
        """
        Get the cheapest possible provider combination.
        
        Returns:
            CostEstimate with cheapest providers for each category
        """
        categories = ["script", "voice", "media", "video_ai", "assembly"]
        cheapest_providers = {}
        
        for category in categories:
            providers = self.compare_providers(category)
            if providers:
                # Get cheapest provider for this category
                cheapest_providers[category] = providers[0]["provider"]
            else:
                cheapest_providers[category] = None
        
        return self.estimate_cost(cheapest_providers)
    
    def get_all_pricing(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all provider pricing organized by category.
        
        Returns:
            Dictionary mapping category to list of provider pricing info
        """
        result = {}
        
        for category in ["script", "voice", "media", "video_ai", "assembly"]:
            result[category] = self.compare_providers(category)
        
        return result
    
    def format_cost_summary(
        self,
        estimate: CostEstimate,
    ) -> str:
        """
        Format a cost estimate as a human-readable summary.
        
        Args:
            estimate: CostEstimate to format
            
        Returns:
            Formatted string summary
        """
        lines = ["Estimated Cost Per Video", "=" * 30]
        
        for item in estimate.breakdown:
            if item.provider:
                lines.append(f"{item.category.title():15} ({item.provider_name}): ${item.cost:.2f}")
            else:
                lines.append(f"{item.category.title():15} Not configured")
        
        lines.append("-" * 30)
        lines.append(f"{'Total':15} ${estimate.total_cost:.2f}")
        lines.append("")
        lines.append(f"Note: {estimate.assumptions}")
        
        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_provider_cost(provider: str) -> float:
    """
    Get estimated cost for a provider without db access.
    
    Args:
        provider: Provider name
        
    Returns:
        Estimated cost per video
    """
    pricing = PROVIDER_PRICING.get(provider, {})
    return pricing.get("estimated_per_video", 0.0)


def estimate_total_cost(providers: Dict[str, str]) -> float:
    """
    Quick estimate of total cost without detailed breakdown.
    
    Args:
        providers: Dictionary mapping category to provider
        
    Returns:
        Total estimated cost
    """
    total = 0.0
    
    for provider in providers.values():
        if provider:
            total += get_provider_cost(provider)
    
    return round(total, 2)
