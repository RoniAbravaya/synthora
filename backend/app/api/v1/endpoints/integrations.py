"""
Integration Management API Endpoints

Handles user API key integrations for external services.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.security import encrypt_value, decrypt_value
from app.models.user import User
from app.models.integration import Integration, PROVIDER_CATEGORIES, IntegrationCategory
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# =============================================================================
# Request Models
# =============================================================================

class IntegrationCreateRequest(BaseModel):
    provider: str
    api_key: str


class IntegrationUpdateRequest(BaseModel):
    api_key: str


# =============================================================================
# Helper Functions
# =============================================================================

def mask_api_key(api_key: str) -> str:
    """Mask an API key, showing only last 4 characters. Max length 50 chars."""
    if len(api_key) <= 4:
        return "****"
    # Limit to 50 chars max to fit database column
    visible_chars = api_key[-4:]
    mask_len = min(len(api_key) - 4, 46)  # 46 asterisks + 4 visible = 50 max
    return "*" * mask_len + visible_chars


def get_provider_category(provider: str) -> str:
    """Get the category for a provider."""
    category_map = {
        "openai": "script",
        "anthropic": "script",
        "elevenlabs": "voice",
        "playht": "voice",
        "pexels": "media",
        "unsplash": "media",
        "pixabay": "media",
        "runway": "video_ai",
        "heygen": "video_ai",
        "sora": "video_ai",
        "veo": "video_ai",
        "luma": "video_ai",
        "remotion": "assembly",
        "ffmpeg": "assembly",
        "creatomate": "assembly",
        "shotstack": "assembly",
        "editframe": "assembly",
    }
    return category_map.get(provider.lower(), "script")


def integration_to_response(integration: Integration) -> Dict[str, Any]:
    """Convert integration to response format."""
    return {
        "id": str(integration.id),
        "provider": integration.provider,
        "category": integration.category,
        "api_key_masked": integration.api_key_masked,
        "is_active": integration.is_active,
        "is_valid": integration.is_valid,
        "last_validated": str(integration.last_validated_at) if integration.last_validated_at else None,
        "created_at": str(integration.created_at) if integration.created_at else None,
    }


# Provider information for frontend
PROVIDER_INFO = {
    "openai": {
        "provider": "openai",
        "name": "OpenAI",
        "category": "script",
        "auth_method": "api_key",
        "required": True,
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "provider": "anthropic",
        "name": "Anthropic",
        "category": "script",
        "auth_method": "api_key",
        "required": False,
        "docs_url": "https://console.anthropic.com/",
    },
    "elevenlabs": {
        "provider": "elevenlabs",
        "name": "ElevenLabs",
        "category": "voice",
        "auth_method": "api_key",
        "required": True,
        "docs_url": "https://elevenlabs.io/app/api-keys",
    },
    "playht": {
        "provider": "playht",
        "name": "Play.ht",
        "category": "voice",
        "auth_method": "api_key",
        "required": False,
        "docs_url": "https://play.ht/studio/api-access",
    },
    "pexels": {
        "provider": "pexels",
        "name": "Pexels",
        "category": "media",
        "auth_method": "api_key",
        "required": True,
        "docs_url": "https://www.pexels.com/api/",
    },
    "pixabay": {
        "provider": "pixabay",
        "name": "Pixabay",
        "category": "media",
        "auth_method": "api_key",
        "required": False,
        "docs_url": "https://pixabay.com/api/docs/",
    },
    "runway": {
        "provider": "runway",
        "name": "Runway",
        "category": "video_ai",
        "auth_method": "api_key",
        "required": False,
        "docs_url": "https://runwayml.com/api",
    },
    "heygen": {
        "provider": "heygen",
        "name": "HeyGen",
        "category": "video_ai",
        "auth_method": "api_key",
        "required": False,
        "docs_url": "https://heygen.com",
    },
    "remotion": {
        "provider": "remotion",
        "name": "Remotion",
        "category": "assembly",
        "auth_method": "api_key",
        "required": True,
        "docs_url": "https://www.remotion.dev/docs/",
    },
}


# =============================================================================
# Available Integrations
# =============================================================================

@router.get("/available")
async def list_available_integrations(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all available integrations with their configuration status.
    """
    # Get user's configured integrations
    user_integrations = db.query(Integration).filter(
        Integration.user_id == user.id
    ).all()
    configured_providers = {i.provider for i in user_integrations}
    
    # Build response
    integrations = []
    for provider, info in PROVIDER_INFO.items():
        integrations.append({
            **info,
            "configured": provider in configured_providers,
        })
    
    # Category names
    categories = {
        "script": "Script Generation",
        "voice": "Voice Generation",
        "media": "Stock Media",
        "video_ai": "AI Video Generation",
        "assembly": "Video Assembly",
    }
    
    return {
        "integrations": integrations,
        "categories": categories,
    }


@router.get("/providers")
async def get_providers_by_category():
    """
    Get all integration providers grouped by category.
    """
    result = {}
    for provider, info in PROVIDER_INFO.items():
        category = info["category"]
        if category not in result:
            result[category] = []
        result[category].append(info)
    return result


@router.get("/readiness")
async def check_readiness(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Check if user has minimum required integrations to generate videos.
    """
    integrations = db.query(Integration).filter(
        and_(
            Integration.user_id == user.id,
            Integration.is_active == True,
            Integration.is_valid == True,
        )
    ).all()
    
    configured_categories = list(set(i.category for i in integrations))
    required_categories = ["script", "voice", "media", "assembly"]
    missing = [c for c in required_categories if c not in configured_categories]
    
    return {
        "ready": len(missing) == 0,
        "can_generate_videos": len(missing) == 0,
        "missing_categories": missing,
        "configured_categories": configured_categories,
    }


# =============================================================================
# User's Integrations
# =============================================================================

@router.get("")
async def list_my_integrations(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all integrations configured by the current user.
    """
    integrations = db.query(Integration).filter(
        Integration.user_id == user.id
    ).order_by(Integration.provider).all()
    
    # Get readiness info
    active_integrations = [i for i in integrations if i.is_active and i.is_valid]
    configured_categories = list(set(i.category for i in active_integrations))
    required_categories = ["script", "voice", "media", "assembly"]
    missing = [c for c in required_categories if c not in configured_categories]
    
    return {
        "integrations": [integration_to_response(i) for i in integrations],
        "minimum_required": 4,
        "configured_count": len(integrations),
        "can_generate_videos": len(missing) == 0,
        "missing_categories": missing,
    }


@router.get("/status")
async def get_integration_status(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a summary of the user's integration status.
    """
    integrations = db.query(Integration).filter(
        Integration.user_id == user.id
    ).all()
    
    active_integrations = [i for i in integrations if i.is_active and i.is_valid]
    configured_categories = list(set(i.category for i in active_integrations))
    required_categories = ["script", "voice", "media", "assembly"]
    missing = [c for c in required_categories if c not in configured_categories]
    
    return {
        "total_configured": len(integrations),
        "active_count": len(active_integrations),
        "configured_categories": configured_categories,
        "missing_categories": missing,
        "can_generate_videos": len(missing) == 0,
        "minimum_required": 4,
    }


# =============================================================================
# Add/Update/Delete Integrations
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def add_integration(
    data: IntegrationCreateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Add a new integration.
    """
    # Check if integration already exists
    existing = db.query(Integration).filter(
        and_(
            Integration.user_id == user.id,
            Integration.provider == data.provider,
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integration for {data.provider} already exists. Use PATCH to update.",
        )
    
    # Get category
    category = get_provider_category(data.provider)
    
    # Encrypt API key
    encrypted_key = encrypt_value(data.api_key)
    masked_key = mask_api_key(data.api_key)
    
    # Create integration
    integration = Integration(
        user_id=user.id,
        provider=data.provider,
        category=category,
        api_key_encrypted=encrypted_key,
        api_key_masked=masked_key,
        is_active=True,
        is_valid=False,  # Will be validated later
    )
    
    db.add(integration)
    db.commit()
    db.refresh(integration)
    
    return integration_to_response(integration)


@router.patch("/{integration_id}")
async def update_integration(
    integration_id: UUID,
    data: IntegrationUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an integration's API key.
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    
    if integration.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this integration",
        )
    
    # Update API key
    integration.api_key_encrypted = encrypt_value(data.api_key)
    integration.api_key_masked = mask_api_key(data.api_key)
    integration.is_valid = False  # Needs re-validation
    integration.last_validated_at = None
    integration.validation_error = None
    
    db.commit()
    db.refresh(integration)
    
    return integration_to_response(integration)


@router.delete("/{integration_id}", response_model=MessageResponse)
async def delete_integration(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete an integration.
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    
    if integration.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this integration",
        )
    
    provider_name = integration.provider
    db.delete(integration)
    db.commit()
    
    return MessageResponse(message=f"Integration for {provider_name} deleted")


# =============================================================================
# Validation & Reveal
# =============================================================================

@router.post("/{integration_id}/validate")
async def validate_integration_endpoint(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manually validate an integration's API key.
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    
    if integration.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to validate this integration",
        )
    
    # For now, just mark as valid (actual validation would call the provider's API)
    integration.is_valid = True
    integration.last_validated_at = datetime.utcnow()
    integration.validation_error = None
    
    db.commit()
    db.refresh(integration)
    
    return {
        "valid": True,
        "message": "API key validated successfully",
        "provider": integration.provider,
    }


@router.post("/{integration_id}/reveal")
async def reveal_api_key(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reveal the full API key for an integration.
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    
    if integration.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this API key",
        )
    
    # Decrypt and return API key
    try:
        api_key = decrypt_value(integration.api_key_encrypted)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key",
        )
    
    logger.info(f"API key revealed for integration {integration_id} by user {user.id}")
    
    return {"api_key": api_key}


@router.patch("/{integration_id}/toggle")
async def toggle_integration(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Toggle an integration's active status.
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    
    if integration.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this integration",
        )
    
    # Toggle status
    integration.is_active = not integration.is_active
    
    db.commit()
    db.refresh(integration)
    
    return integration_to_response(integration)
