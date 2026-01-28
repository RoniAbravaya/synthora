"""
User Generation Settings API Endpoints

Endpoints for managing user's video generation preferences:
- Default provider selection per category
- Subtitle style preferences
- Cost estimation
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.services.user_generation_settings import UserGenerationSettingsService
from app.services.cost_estimation import CostEstimationService
from app.schemas.user_generation_settings import (
    UserGenerationSettingsResponse,
    UserGenerationSettingsUpdate,
    CostEstimateResponse,
    CostBreakdownItem,
    AvailableProvidersResponse,
    CategoryProviders,
    ProviderInfo,
    SubtitleStyleInfo,
    EffectiveProvidersResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/generation", tags=["Generation Settings"])


@router.get("", response_model=UserGenerationSettingsResponse)
async def get_generation_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user's generation settings.
    
    Returns default provider selections and subtitle style.
    Creates default settings if not exists.
    """
    service = UserGenerationSettingsService(db)
    settings = service.get_settings(current_user.id)
    
    return UserGenerationSettingsResponse(
        id=str(settings.id),
        user_id=str(settings.user_id),
        default_script_provider=settings.default_script_provider,
        default_voice_provider=settings.default_voice_provider,
        default_media_provider=settings.default_media_provider,
        default_video_ai_provider=settings.default_video_ai_provider,
        default_assembly_provider=settings.default_assembly_provider,
        subtitle_style=settings.subtitle_style,
        created_at=str(settings.created_at) if settings.created_at else None,
        updated_at=str(settings.updated_at) if settings.updated_at else None,
    )


@router.put("", response_model=UserGenerationSettingsResponse)
async def update_generation_settings(
    updates: UserGenerationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update user's generation settings.
    
    Only provided fields will be updated.
    """
    service = UserGenerationSettingsService(db)
    
    try:
        # Convert to dict, excluding None values
        update_dict = updates.model_dump(exclude_none=True)
        
        settings = service.update_settings(current_user.id, update_dict)
        
        return UserGenerationSettingsResponse(
            id=str(settings.id),
            user_id=str(settings.user_id),
            default_script_provider=settings.default_script_provider,
            default_voice_provider=settings.default_voice_provider,
            default_media_provider=settings.default_media_provider,
            default_video_ai_provider=settings.default_video_ai_provider,
            default_assembly_provider=settings.default_assembly_provider,
            subtitle_style=settings.subtitle_style,
            created_at=str(settings.created_at) if settings.created_at else None,
            updated_at=str(settings.updated_at) if settings.updated_at else None,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/cost-estimate", response_model=CostEstimateResponse)
async def get_cost_estimate(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get estimated cost per video based on current settings.
    
    Returns breakdown by category and total estimated cost.
    """
    cost_service = CostEstimationService(db)
    estimate = cost_service.estimate_cost_for_user(current_user.id)
    
    return CostEstimateResponse(
        breakdown=[
            CostBreakdownItem(
                category=item.category,
                provider=item.provider,
                provider_name=item.provider_name,
                cost=item.cost,
                unit=item.unit,
                description=item.description,
            )
            for item in estimate.breakdown
        ],
        total_cost=estimate.total_cost,
        currency=estimate.currency,
        assumptions=estimate.assumptions,
    )


@router.get("/available-providers", response_model=AvailableProvidersResponse)
async def get_available_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get available providers for each category based on user's integrations.
    
    Only returns providers that the user has configured.
    """
    settings_service = UserGenerationSettingsService(db)
    
    # Get available providers
    available = settings_service.get_available_providers(current_user.id)
    
    # Convert to response format
    providers = CategoryProviders(
        script=[
            ProviderInfo(**p) for p in available.get("script", [])
        ],
        voice=[
            ProviderInfo(**p) for p in available.get("voice", [])
        ],
        media=[
            ProviderInfo(**p) for p in available.get("media", [])
        ],
        video_ai=[
            ProviderInfo(**p) for p in available.get("video_ai", [])
        ],
        assembly=[
            ProviderInfo(**p) for p in available.get("assembly", [])
        ],
    )
    
    # Get subtitle styles
    subtitle_styles = [
        SubtitleStyleInfo(**style)
        for style in settings_service.get_subtitle_styles()
    ]
    
    return AvailableProvidersResponse(
        providers=providers,
        subtitle_styles=subtitle_styles,
    )


@router.get("/effective-providers", response_model=EffectiveProvidersResponse)
async def get_effective_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the effective provider for each category.
    
    Returns user's default if set and available, otherwise first available.
    """
    settings_service = UserGenerationSettingsService(db)
    effective = settings_service.get_effective_providers(current_user.id)
    
    return EffectiveProvidersResponse(
        script=effective.get("script"),
        voice=effective.get("voice"),
        media=effective.get("media"),
        video_ai=effective.get("video_ai"),
        assembly=effective.get("assembly"),
    )


@router.get("/subtitle-config")
async def get_subtitle_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the subtitle style configuration for the current user.
    
    Returns the full ASS format configuration for FFmpeg.
    """
    settings_service = UserGenerationSettingsService(db)
    config = settings_service.get_subtitle_config(current_user.id)
    
    return config
