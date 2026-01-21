"""
Integration Pydantic Schemas

Request and response schemas for integration-related endpoints.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.integration import IntegrationProvider, IntegrationCategory


# =============================================================================
# Response Schemas
# =============================================================================

class IntegrationResponse(IDSchema, TimestampSchema):
    """Integration response with masked API key."""
    
    provider: IntegrationProvider
    category: IntegrationCategory
    is_active: bool
    is_validated: bool
    validated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    error_message: Optional[str] = None
    api_key_masked: str = Field(description="Masked API key (last 4 chars visible)")


class IntegrationRevealResponse(BaseSchema):
    """Response with full API key (for reveal feature)."""
    
    api_key: str = Field(description="Full decrypted API key")


class AvailableIntegration(BaseSchema):
    """Information about an available integration."""
    
    provider: str = Field(description="Provider identifier")
    name: str = Field(description="Display name")
    category: str = Field(description="Integration category")
    auth_method: str = Field(description="Authentication method (api_key, oauth, none)")
    required: bool = Field(description="Whether this category is required")
    docs_url: Optional[str] = Field(default=None, description="Documentation URL")
    configured: bool = Field(description="Whether user has configured this")


class AvailableIntegrationsResponse(BaseSchema):
    """List of available integrations."""
    
    integrations: List[AvailableIntegration]
    categories: dict = Field(description="Category name mappings")


class UserIntegrationsResponse(BaseSchema):
    """User's configured integrations."""
    
    integrations: List[IntegrationResponse]
    minimum_required: int = Field(default=4, description="Minimum integrations required")
    configured_count: int = Field(description="Number configured")
    can_generate_videos: bool = Field(description="Has enough integrations to generate")
    missing_categories: List[str] = Field(description="Required categories not configured")


# =============================================================================
# Request Schemas
# =============================================================================

class IntegrationCreate(BaseSchema):
    """Schema for adding a new integration."""
    
    provider: IntegrationProvider = Field(description="Integration provider")
    api_key: str = Field(min_length=1, description="API key for the service")


class IntegrationUpdate(BaseSchema):
    """Schema for updating an integration."""
    
    api_key: str = Field(min_length=1, description="New API key")


class IntegrationValidateResponse(BaseSchema):
    """Validation result response."""
    
    valid: bool = Field(description="Whether the API key is valid")
    message: str = Field(description="Validation message")
    provider: str = Field(description="Provider that was validated")

