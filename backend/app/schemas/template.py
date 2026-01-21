"""
Template Pydantic Schemas

Request and response schemas for template-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.template import (
    TemplateCategory,
    AspectRatio,
    HookStyle,
    NarrativeStructure,
    Pacing,
    VisualAesthetic,
    VoiceTone,
    MusicMood,
    CTAType,
)


# =============================================================================
# Nested Config Schemas
# =============================================================================

class VideoStructureConfig(BaseSchema):
    """Video structure configuration."""
    
    hook_style: HookStyle = HookStyle.QUESTION
    narrative_structure: NarrativeStructure = NarrativeStructure.HOOK_PROBLEM_SOLUTION_CTA
    num_scenes: int = Field(default=5, ge=1, le=20)
    duration_min: int = Field(default=15, ge=5, le=600)
    duration_max: int = Field(default=60, ge=5, le=600)
    pacing: Pacing = Pacing.MEDIUM


class VisualStyleConfig(BaseSchema):
    """Visual style configuration."""
    
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    color_palette: Dict[str, str] = Field(default_factory=dict)
    visual_aesthetic: VisualAesthetic = VisualAesthetic.CINEMATIC
    transitions: str = "cut"
    filter_mood: str = "neutral"


class TextCaptionsConfig(BaseSchema):
    """Text and captions configuration."""
    
    caption_style: str = "bold_popup"
    font_style: str = "modern"
    text_position: str = "bottom"
    hook_text_overlay: bool = True


class AudioConfig(BaseSchema):
    """Audio configuration."""
    
    voice_gender: str = "neutral"
    voice_tone: VoiceTone = VoiceTone.PROFESSIONAL
    voice_speed: str = "normal"
    music_mood: MusicMood = MusicMood.UPBEAT
    sound_effects: bool = True


class ScriptPromptConfig(BaseSchema):
    """Script/prompt configuration."""
    
    script_structure_prompt: Optional[str] = None
    tone_instructions: Optional[str] = None
    cta_type: CTAType = CTAType.FOLLOW
    cta_placement: str = "end"


class PlatformOptimizationConfig(BaseSchema):
    """Platform optimization configuration."""
    
    thumbnail_style: str = "title_overlay"
    suggested_hashtags: List[str] = Field(default_factory=list)


# =============================================================================
# Request Schemas
# =============================================================================

class TemplateCreate(BaseSchema):
    """Schema for creating a new template."""
    
    name: str = Field(min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    category: TemplateCategory = TemplateCategory.GENERAL
    target_platforms: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
    # Nested configs
    video_structure: Optional[VideoStructureConfig] = None
    visual_style: Optional[VisualStyleConfig] = None
    text_captions: Optional[TextCaptionsConfig] = None
    audio: Optional[AudioConfig] = None
    script_prompt: Optional[ScriptPromptConfig] = None
    platform_optimization: Optional[PlatformOptimizationConfig] = None
    
    # For system templates (admin only)
    is_system: bool = False
    is_public: bool = False


class TemplateUpdate(BaseSchema):
    """Schema for updating a template."""
    
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    category: Optional[TemplateCategory] = None
    target_platforms: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    
    # Nested configs
    video_structure: Optional[VideoStructureConfig] = None
    visual_style: Optional[VisualStyleConfig] = None
    text_captions: Optional[TextCaptionsConfig] = None
    audio: Optional[AudioConfig] = None
    script_prompt: Optional[ScriptPromptConfig] = None
    platform_optimization: Optional[PlatformOptimizationConfig] = None
    
    is_public: Optional[bool] = None


# =============================================================================
# Response Schemas
# =============================================================================

class TemplateResponse(IDSchema, TimestampSchema):
    """Full template response."""
    
    user_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    category: TemplateCategory
    target_platforms: List[str]
    tags: List[str]
    
    # Flattened config (for simplicity in response)
    hook_style: HookStyle
    narrative_structure: NarrativeStructure
    num_scenes: int
    duration_min: int
    duration_max: int
    pacing: Pacing
    aspect_ratio: AspectRatio
    visual_aesthetic: VisualAesthetic
    voice_tone: VoiceTone
    music_mood: MusicMood
    cta_type: CTAType
    
    is_system: bool
    is_public: bool
    version: int


class TemplateListItem(IDSchema):
    """Simplified template for list views."""
    
    name: str
    description: Optional[str] = None
    category: TemplateCategory
    target_platforms: List[str]
    is_system: bool
    is_public: bool
    version: int
    created_at: datetime


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

