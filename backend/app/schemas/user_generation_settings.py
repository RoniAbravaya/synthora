"""
User Generation Settings Schemas

Pydantic schemas for user generation settings API endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    """Information about a provider."""
    provider: str
    display_name: str
    is_valid: bool = False
    estimated_cost: float = 0.0


class CategoryProviders(BaseModel):
    """Available providers for a category."""
    script: List[ProviderInfo] = []
    voice: List[ProviderInfo] = []
    media: List[ProviderInfo] = []
    video_ai: List[ProviderInfo] = []
    assembly: List[ProviderInfo] = []


class SubtitleStyleInfo(BaseModel):
    """Information about a subtitle style."""
    name: str
    display_name: str
    description: str
    is_default: bool = False
    preview: Dict[str, Any] = {}


class UserGenerationSettingsResponse(BaseModel):
    """Response for user generation settings."""
    id: str
    user_id: str
    default_script_provider: Optional[str] = None
    default_voice_provider: Optional[str] = None
    default_media_provider: Optional[str] = None
    default_video_ai_provider: Optional[str] = None
    default_assembly_provider: Optional[str] = None
    subtitle_style: str = "modern"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserGenerationSettingsUpdate(BaseModel):
    """Request to update user generation settings."""
    default_script_provider: Optional[str] = Field(
        None, description="Default provider for script generation"
    )
    default_voice_provider: Optional[str] = Field(
        None, description="Default provider for voice generation"
    )
    default_media_provider: Optional[str] = Field(
        None, description="Default provider for stock media"
    )
    default_video_ai_provider: Optional[str] = Field(
        None, description="Default provider for AI video generation"
    )
    default_assembly_provider: Optional[str] = Field(
        None, description="Default provider for video assembly"
    )
    subtitle_style: Optional[str] = Field(
        None, description="Subtitle style preset (classic, modern, bold, minimal)"
    )


class CostBreakdownItem(BaseModel):
    """Cost breakdown for a single category."""
    category: str
    provider: Optional[str]
    provider_name: str
    cost: float
    unit: str
    description: str


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""
    breakdown: List[CostBreakdownItem]
    total_cost: float
    currency: str = "USD"
    assumptions: str


class AvailableProvidersResponse(BaseModel):
    """Response with available providers per category."""
    providers: CategoryProviders
    subtitle_styles: List[SubtitleStyleInfo]


class EffectiveProvidersResponse(BaseModel):
    """Response with effective providers (user defaults or first available)."""
    script: Optional[str] = None
    voice: Optional[str] = None
    media: Optional[str] = None
    video_ai: Optional[str] = None
    assembly: Optional[str] = None
