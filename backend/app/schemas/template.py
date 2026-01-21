"""
Template Pydantic Schemas

Request and response schemas for template-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Nested Config Schemas
# =============================================================================

class VideoStructureConfig(BaseSchema):
    """Video structure configuration."""
    
    hook_style: str = "question"
    narrative_structure: str = "hook_story_payoff"
    duration_seconds: int = Field(default=60, ge=5, le=600)
    aspect_ratio: str = "9:16"
    segments: Optional[List[Dict[str, Any]]] = None


class VisualStyleConfig(BaseSchema):
    """Visual style configuration."""
    
    color_scheme: str = "modern"
    font_family: str = "Inter"
    transition_style: str = "cut"
    overlay_style: str = "minimal"


class AudioConfig(BaseSchema):
    """Audio configuration."""
    
    voice_style: str = "professional"
    background_music_genre: str = "upbeat"
    sound_effects: bool = True


class ScriptPromptConfig(BaseSchema):
    """Script/prompt configuration."""
    
    tone: str = "professional"
    hook_style: str = "question"
    call_to_action: str = "Follow for more"
    content_structure: List[str] = Field(default=["hook", "problem", "solution", "cta"])


class PlatformOptimizationConfig(BaseSchema):
    """Platform optimization configuration."""
    
    primary_platform: str = "tiktok"
    hashtag_strategy: str = "trending"
    caption_style: str = "engaging"


class TemplateConfigSchema(BaseSchema):
    """Full template configuration."""
    
    video_structure: Optional[VideoStructureConfig] = None
    visual_style: Optional[VisualStyleConfig] = None
    audio: Optional[AudioConfig] = None
    script_prompt: Optional[ScriptPromptConfig] = None
    platform_optimization: Optional[PlatformOptimizationConfig] = None


# =============================================================================
# Request Schemas
# =============================================================================

class TemplateCreate(BaseSchema):
    """Schema for creating a new template."""
    
    name: str = Field(min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    is_public: bool = False
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TemplateUpdate(BaseSchema):
    """Schema for updating a template."""
    
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


# =============================================================================
# Response Schemas
# =============================================================================

class TemplateResponse(IDSchema, TimestampSchema):
    """Full template response."""
    
    user_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    category: str
    tags: List[str] = Field(default_factory=list)
    is_system: bool
    is_public: bool
    is_premium: bool = False
    is_featured: bool = False
    use_count: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)


class TemplateListItem(IDSchema):
    """Simplified template for list views."""
    
    name: str
    description: Optional[str] = None
    category: str
    tags: List[str] = Field(default_factory=list)
    is_system: bool
    is_public: bool
    is_premium: bool = False
    is_featured: bool = False
    use_count: int = 0
    created_at: Optional[datetime] = None


class TemplateListResponse(BaseSchema):
    """Paginated template list."""
    
    templates: List[TemplateListItem]
    total: int
    skip: int
    limit: int


class TemplateConfigResponse(BaseSchema):
    """Full template configuration for video generation."""
    
    id: UUID
    name: str
    config: Dict[str, Any] = Field(description="Full template configuration")
