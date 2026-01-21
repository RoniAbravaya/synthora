"""
Integration Management API Endpoints

Handles user API key integrations for external services.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.services.integration import IntegrationService, get_integration_service
from app.models.user import User
from app.models.integration import IntegrationProvider, IntegrationCategory
from app.integrations import validate_integration
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    IntegrationRevealResponse,
    AvailableIntegration,
    AvailableIntegrationsResponse,
    UserIntegrationsResponse,
    IntegrationValidateResponse,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# =============================================================================
# Available Integrations (Public Info)
# =============================================================================

@router.get("/available", response_model=AvailableIntegrationsResponse)
async def list_available_integrations(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all available integrations with their configuration status.
    
    Returns all supported integrations grouped by category,
    with information about which ones the user has configured.
    
    **Requires:** Authentication
    """
    integration_service = IntegrationService(db)
    
    # Get user's configured integrations
    user_integrations = integration_service.get_user_integrations(user.id)
    configured_providers = {i.provider for i in user_integrations}
    
    # Build response
    integrations = []
    for provider in IntegrationProvider:
        info = IntegrationService.get_provider_info(provider)
        integrations.append(
            AvailableIntegration(
                provider=info["provider"],
                name=info["name"],
                category=info["category"],
                auth_method=info["auth_method"],
                required=info["required"],
                docs_url=info["docs_url"],
                configured=provider in configured_providers,
            )
        )
    
    # Category name mappings
    categories = {
        cat.value: cat.value.replace("_", " ").title()
        for cat in IntegrationCategory
    }
    
    return AvailableIntegrationsResponse(
        integrations=integrations,
        categories=categories,
    )


@router.get("/providers", response_model=dict)
async def get_providers_by_category():
    """
    Get all integration providers grouped by category.
    
    Useful for displaying integrations in the UI organized by type.
    
    **No authentication required** (public info)
    """
    return IntegrationService.get_providers_by_category()


# =============================================================================
# User's Integrations
# =============================================================================

@router.get("", response_model=UserIntegrationsResponse)
async def list_my_integrations(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all integrations configured by the current user.
    
    Returns:
    - List of configured integrations with masked API keys
    - Count of configured integrations
    - Whether user can generate videos (has minimum required)
    - Missing required categories
    
    **Requires:** Authentication
    """
    integration_service = IntegrationService(db)
    
    integrations = integration_service.get_user_integrations(user.id)
    status_info = integration_service.get_integration_status(user.id)
    
    # Build integration responses with masked keys
    integration_responses = []
    for i in integrations:
        integration_responses.append(
            IntegrationResponse(
                id=i.id,
                provider=i.provider,
                category=i.category,
                is_active=i.is_active,
                is_validated=i.is_validated,
                validated_at=i.validated_at,
                last_used_at=i.last_used_at,
                error_message=i.error_message,
                api_key_masked=integration_service.get_masked_api_key(i),
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
        )
    
    return UserIntegrationsResponse(
        integrations=integration_responses,
        minimum_required=status_info["minimum_required"],
        configured_count=status_info["total_configured"],
        can_generate_videos=status_info["can_generate_videos"],
        missing_categories=status_info["missing_categories"],
    )


@router.get("/status", response_model=dict)
async def get_integration_status(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a summary of the user's integration status.
    
    Quick check to see if user has enough integrations
    to start generating videos.
    
    **Requires:** Authentication
    """
    integration_service = IntegrationService(db)
    return integration_service.get_integration_status(user.id)


# =============================================================================
# Add/Update/Delete Integrations
# =============================================================================

@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def add_integration(
    data: IntegrationCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Add a new integration.
    
    The API key will be encrypted before storage.
    Validation will be performed in the background.
    
    **Request Body:**
    - `provider`: Integration provider (e.g., "openai", "elevenlabs")
    - `api_key`: The API key for the service
    
    **Requires:** Authentication
    """
    integration_service = IntegrationService(db)
    
    # Check if integration already exists
    existing = integration_service.get_by_provider(user.id, data.provider)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integration for {data.provider.value} already exists. Use PATCH to update.",
        )
    
    # Add the integration
    integration = integration_service.add_integration(
        user_id=user.id,
        provider=data.provider,
        api_key=data.api_key,
    )
    
    # Schedule validation in background
    background_tasks.add_task(
        _validate_integration_background,
        db,
        integration.id,
        data.provider,
        data.api_key,
    )
    
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        category=integration.category,
        is_active=integration.is_active,
        is_validated=integration.is_validated,
        validated_at=integration.validated_at,
        last_used_at=integration.last_used_at,
        error_message=integration.error_message,
        api_key_masked=integration_service.get_masked_api_key(integration),
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    data: IntegrationUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an integration's API key.
    
    The new API key will be encrypted and the integration
    will be re-validated in the background.
    
    **Path Parameters:**
    - `integration_id`: UUID of the integration
    
    **Request Body:**
    - `api_key`: New API key
    
    **Requires:** Authentication (must own the integration)
    """
    integration_service = IntegrationService(db)
    
    integration = integration_service.get_by_id(integration_id)
    
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
    
    # Update the API key
    integration = integration_service.update_api_key(integration, data.api_key)
    
    # Schedule re-validation in background
    background_tasks.add_task(
        _validate_integration_background,
        db,
        integration.id,
        integration.provider,
        data.api_key,
    )
    
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        category=integration.category,
        is_active=integration.is_active,
        is_validated=integration.is_validated,
        validated_at=integration.validated_at,
        last_used_at=integration.last_used_at,
        error_message=integration.error_message,
        api_key_masked=integration_service.get_masked_api_key(integration),
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.delete("/{integration_id}", response_model=MessageResponse)
async def delete_integration(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete an integration.
    
    **Path Parameters:**
    - `integration_id`: UUID of the integration
    
    **Requires:** Authentication (must own the integration)
    """
    integration_service = IntegrationService(db)
    
    integration = integration_service.get_by_id(integration_id)
    
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
    
    provider_name = integration.provider.value
    integration_service.delete_integration(integration)
    
    return MessageResponse(message=f"Integration for {provider_name} deleted")


# =============================================================================
# Validation & Reveal
# =============================================================================

@router.post("/{integration_id}/validate", response_model=IntegrationValidateResponse)
async def validate_integration_endpoint(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manually validate an integration's API key.
    
    This makes a test request to the provider's API to verify
    the API key is valid.
    
    **Path Parameters:**
    - `integration_id`: UUID of the integration
    
    **Requires:** Authentication (must own the integration)
    """
    integration_service = IntegrationService(db)
    
    integration = integration_service.get_by_id(integration_id)
    
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
    
    # Get decrypted API key
    api_key = integration_service.get_decrypted_api_key(integration)
    
    # Run validation
    result = await validate_integration(integration.provider, api_key)
    
    # Update integration status
    integration_service.set_validation_status(
        integration,
        is_valid=result.valid,
        error_message=result.message if not result.valid else None,
    )
    
    return IntegrationValidateResponse(
        valid=result.valid,
        message=result.message,
        provider=integration.provider.value,
    )


@router.post("/{integration_id}/reveal", response_model=IntegrationRevealResponse)
async def reveal_api_key(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reveal the full API key for an integration.
    
    This decrypts and returns the full API key.
    Use with caution - the key will be visible in the response.
    
    **Path Parameters:**
    - `integration_id`: UUID of the integration
    
    **Requires:** Authentication (must own the integration)
    
    **Security Note:** This endpoint should be rate-limited
    and logged for security auditing.
    """
    integration_service = IntegrationService(db)
    
    integration = integration_service.get_by_id(integration_id)
    
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
    
    # Log the reveal action for security auditing
    logger.info(f"API key revealed for integration {integration_id} by user {user.id}")
    
    api_key = integration_service.get_decrypted_api_key(integration)
    
    return IntegrationRevealResponse(api_key=api_key)


@router.patch("/{integration_id}/toggle", response_model=IntegrationResponse)
async def toggle_integration(
    integration_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Toggle an integration's active status.
    
    Disabled integrations won't be used for video generation.
    
    **Path Parameters:**
    - `integration_id`: UUID of the integration
    
    **Requires:** Authentication (must own the integration)
    """
    integration_service = IntegrationService(db)
    
    integration = integration_service.get_by_id(integration_id)
    
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
    
    # Toggle the status
    integration = integration_service.set_active_status(
        integration,
        is_active=not integration.is_active,
    )
    
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        category=integration.category,
        is_active=integration.is_active,
        is_validated=integration.is_validated,
        validated_at=integration.validated_at,
        last_used_at=integration.last_used_at,
        error_message=integration.error_message,
        api_key_masked=integration_service.get_masked_api_key(integration),
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


# =============================================================================
# Background Tasks
# =============================================================================

async def _validate_integration_background(
    db: Session,
    integration_id: UUID,
    provider: IntegrationProvider,
    api_key: str,
) -> None:
    """
    Background task to validate an integration.
    
    This is run asynchronously after adding/updating an integration.
    """
    try:
        result = await validate_integration(provider, api_key)
        
        # Get a fresh session for the update
        integration_service = IntegrationService(db)
        integration = integration_service.get_by_id(integration_id)
        
        if integration:
            integration_service.set_validation_status(
                integration,
                is_valid=result.valid,
                error_message=result.message if not result.valid else None,
            )
            logger.info(
                f"Background validation for {provider.value}: "
                f"{'valid' if result.valid else 'invalid'}"
            )
    except Exception as e:
        logger.error(f"Background validation error: {e}")
