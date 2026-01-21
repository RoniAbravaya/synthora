"""
Template Management API Endpoints

Handles video generation templates (system and personal).
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_admin
from app.services.template import TemplateService, get_template_service
from app.services.template_validator import validate_template_config
from app.models.user import User, UserRole
from app.models.template import Template, TemplateCategory
from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListItem,
    TemplateListResponse,
    TemplateConfigResponse,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


# =============================================================================
# List Templates
# =============================================================================

@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[TemplateCategory] = Query(default=None, description="Filter by category"),
    platform: Optional[str] = Query(default=None, description="Filter by target platform"),
    search: Optional[str] = Query(default=None, description="Search in name and description"),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Records to return"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all accessible templates.
    
    Returns:
    - System templates (available to all)
    - User's personal templates
    - Public templates from other users
    
    **Query Parameters:**
    - `category`: Filter by template category
    - `platform`: Filter by target platform (youtube, tiktok, instagram, facebook)
    - `search`: Search in name and description
    - `skip`: Pagination offset
    - `limit`: Maximum records to return
    
    **Requires:** Authentication
    """
    template_service = TemplateService(db)
    
    templates, total = template_service.get_accessible_templates(
        user_id=user.id,
        category=category,
        platform=platform,
        search=search,
        skip=skip,
        limit=limit,
    )
    
    template_items = [
        TemplateListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            target_platforms=t.target_platforms or [],
            is_system=t.is_system,
            is_public=t.is_public,
            version=t.version,
            created_at=t.created_at,
        )
        for t in templates
    ]
    
    return TemplateListResponse(
        templates=template_items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/system", response_model=List[TemplateListItem])
async def list_system_templates(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all system templates.
    
    System templates are pre-built templates available to all users.
    
    **Requires:** Authentication
    """
    template_service = TemplateService(db)
    templates = template_service.get_system_templates()
    
    return [
        TemplateListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            target_platforms=t.target_platforms or [],
            is_system=t.is_system,
            is_public=t.is_public,
            version=t.version,
            created_at=t.created_at,
        )
        for t in templates
    ]


@router.get("/my", response_model=List[TemplateListItem])
async def list_my_templates(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List the current user's personal templates.
    
    **Requires:** Authentication
    """
    template_service = TemplateService(db)
    templates = template_service.get_user_templates(user.id)
    
    return [
        TemplateListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            target_platforms=t.target_platforms or [],
            is_system=t.is_system,
            is_public=t.is_public,
            version=t.version,
            created_at=t.created_at,
        )
        for t in templates
    ]


# =============================================================================
# Get Single Template
# =============================================================================

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a template by ID.
    
    **Path Parameters:**
    - `template_id`: UUID of the template
    
    **Requires:** Authentication (must have access to the template)
    """
    template_service = TemplateService(db)
    template = template_service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    if not template_service.can_access_template(template, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this template",
        )
    
    return _template_to_response(template)


@router.get("/{template_id}/config", response_model=TemplateConfigResponse)
async def get_template_config(
    template_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the full configuration for a template.
    
    Returns the template configuration in a format suitable
    for the video generation pipeline.
    
    **Path Parameters:**
    - `template_id`: UUID of the template
    
    **Requires:** Authentication (must have access to the template)
    """
    template_service = TemplateService(db)
    template = template_service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    if not template_service.can_access_template(template, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this template",
        )
    
    config = template_service.get_template_config(template)
    
    return TemplateConfigResponse(
        id=template.id,
        name=template.name,
        config=config,
    )


# =============================================================================
# Create Template
# =============================================================================

@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal template.
    
    **Request Body:**
    - `name`: Template name (required)
    - `description`: Template description
    - `category`: Template category
    - `target_platforms`: List of target platforms
    - `tags`: Searchable tags
    - Configuration sections (video_structure, visual_style, etc.)
    
    **Requires:** Authentication
    
    **Note:** Only admins can create system templates.
    """
    template_service = TemplateService(db)
    
    # Only admins can create system templates
    if data.is_system and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create system templates",
        )
    
    # Build template kwargs from nested configs
    template_kwargs = _extract_template_kwargs(data)
    
    # Create the template
    template = template_service.create_template(
        user_id=None if data.is_system else user.id,
        name=data.name,
        description=data.description,
        category=data.category,
        is_system=data.is_system,
        is_public=data.is_public,
        target_platforms=data.target_platforms,
        tags=data.tags,
        **template_kwargs,
    )
    
    return _template_to_response(template)


# =============================================================================
# Update Template
# =============================================================================

@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a template.
    
    **Path Parameters:**
    - `template_id`: UUID of the template
    
    **Request Body:**
    - Any template fields to update
    
    **Requires:** Authentication (must own the template, or be admin for system templates)
    """
    template_service = TemplateService(db)
    template = template_service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    if not template_service.can_edit_template(template, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this template",
        )
    
    # Build update kwargs
    update_kwargs = {}
    
    if data.name is not None:
        update_kwargs["name"] = data.name
    if data.description is not None:
        update_kwargs["description"] = data.description
    if data.category is not None:
        update_kwargs["category"] = data.category
    if data.target_platforms is not None:
        update_kwargs["target_platforms"] = data.target_platforms
    if data.tags is not None:
        update_kwargs["tags"] = data.tags
    if data.is_public is not None:
        update_kwargs["is_public"] = data.is_public
    
    # Add nested config updates
    update_kwargs.update(_extract_template_kwargs(data))
    
    # Update the template
    template = template_service.update_template(template, **update_kwargs)
    
    return _template_to_response(template)


# =============================================================================
# Delete Template
# =============================================================================

@router.delete("/{template_id}", response_model=MessageResponse)
async def delete_template(
    template_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a template.
    
    **Path Parameters:**
    - `template_id`: UUID of the template
    
    **Requires:** Authentication (must own the template, or be admin for system templates)
    """
    template_service = TemplateService(db)
    template = template_service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    if not template_service.can_edit_template(template, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this template",
        )
    
    template_name = template.name
    template_service.delete_template(template)
    
    return MessageResponse(message=f"Template '{template_name}' deleted")


# =============================================================================
# Duplicate Template
# =============================================================================

@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_template(
    template_id: UUID,
    new_name: Optional[str] = Query(default=None, description="Name for the duplicate"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Duplicate a template.
    
    Creates a personal copy of a template. Useful for customizing
    system templates or public templates from other users.
    
    **Path Parameters:**
    - `template_id`: UUID of the template to duplicate
    
    **Query Parameters:**
    - `new_name`: Optional name for the duplicate
    
    **Requires:** Authentication (must have access to the source template)
    """
    template_service = TemplateService(db)
    template = template_service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    if not template_service.can_access_template(template, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this template",
        )
    
    # Duplicate the template
    new_template = template_service.duplicate_template(
        template=template,
        new_owner_id=user.id,
        new_name=new_name,
    )
    
    return _template_to_response(new_template)


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/seed", response_model=MessageResponse)
async def seed_system_templates(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Seed the database with system templates.
    
    This creates the default system templates if they don't exist.
    
    **Requires:** Admin role
    """
    from app.data.seed_templates import seed_system_templates as do_seed
    
    created = do_seed(db)
    
    return MessageResponse(
        message=f"Seeded {len(created)} system templates"
    )


@router.get("/stats", response_model=dict)
async def get_template_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get template statistics.
    
    **Requires:** Admin role
    """
    template_service = TemplateService(db)
    return template_service.get_template_stats()


# =============================================================================
# Helper Functions
# =============================================================================

def _template_to_response(template: Template) -> TemplateResponse:
    """Convert a Template model to TemplateResponse."""
    return TemplateResponse(
        id=template.id,
        user_id=template.user_id,
        name=template.name,
        description=template.description,
        category=template.category,
        target_platforms=template.target_platforms or [],
        tags=template.tags or [],
        hook_style=template.hook_style,
        narrative_structure=template.narrative_structure,
        num_scenes=template.num_scenes,
        duration_min=template.duration_min,
        duration_max=template.duration_max,
        pacing=template.pacing,
        aspect_ratio=template.aspect_ratio,
        visual_aesthetic=template.visual_aesthetic,
        voice_tone=template.voice_tone,
        music_mood=template.music_mood,
        cta_type=template.cta_type,
        is_system=template.is_system,
        is_public=template.is_public,
        version=template.version,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _extract_template_kwargs(data) -> dict:
    """Extract template configuration kwargs from nested config objects."""
    kwargs = {}
    
    # Video structure
    if data.video_structure:
        vs = data.video_structure
        if vs.hook_style:
            kwargs["hook_style"] = vs.hook_style
        if vs.narrative_structure:
            kwargs["narrative_structure"] = vs.narrative_structure
        if vs.num_scenes:
            kwargs["num_scenes"] = vs.num_scenes
        if vs.duration_min:
            kwargs["duration_min"] = vs.duration_min
        if vs.duration_max:
            kwargs["duration_max"] = vs.duration_max
        if vs.pacing:
            kwargs["pacing"] = vs.pacing
    
    # Visual style
    if data.visual_style:
        vs = data.visual_style
        if vs.aspect_ratio:
            kwargs["aspect_ratio"] = vs.aspect_ratio
        if vs.color_palette:
            kwargs["color_palette"] = vs.color_palette
        if vs.visual_aesthetic:
            kwargs["visual_aesthetic"] = vs.visual_aesthetic
        if vs.transitions:
            kwargs["transitions"] = vs.transitions
        if vs.filter_mood:
            kwargs["filter_mood"] = vs.filter_mood
    
    # Text/Captions
    if data.text_captions:
        tc = data.text_captions
        if tc.caption_style:
            kwargs["caption_style"] = tc.caption_style
        if tc.font_style:
            kwargs["font_style"] = tc.font_style
        if tc.text_position:
            kwargs["text_position"] = tc.text_position
        if tc.hook_text_overlay is not None:
            kwargs["hook_text_overlay"] = tc.hook_text_overlay
    
    # Audio
    if data.audio:
        au = data.audio
        if au.voice_gender:
            kwargs["voice_gender"] = au.voice_gender
        if au.voice_tone:
            kwargs["voice_tone"] = au.voice_tone
        if au.voice_speed:
            kwargs["voice_speed"] = au.voice_speed
        if au.music_mood:
            kwargs["music_mood"] = au.music_mood
        if au.sound_effects is not None:
            kwargs["sound_effects"] = au.sound_effects
    
    # Script/Prompt
    if data.script_prompt:
        sp = data.script_prompt
        if sp.script_structure_prompt:
            kwargs["script_structure_prompt"] = sp.script_structure_prompt
        if sp.tone_instructions:
            kwargs["tone_instructions"] = sp.tone_instructions
        if sp.cta_type:
            kwargs["cta_type"] = sp.cta_type
        if sp.cta_placement:
            kwargs["cta_placement"] = sp.cta_placement
    
    # Platform optimization
    if data.platform_optimization:
        po = data.platform_optimization
        if po.thumbnail_style:
            kwargs["thumbnail_style"] = po.thumbnail_style
        if po.suggested_hashtags:
            kwargs["suggested_hashtags"] = po.suggested_hashtags
    
    return kwargs
