"""
Template Service

Business logic for managing video generation templates.
Templates define the structure, style, and configuration for video generation.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import copy

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.template import (
    Template,
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
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class TemplateService:
    """
    Service class for template management operations.
    
    Handles:
    - CRUD operations for templates
    - System vs personal template management
    - Template duplication
    - Template configuration export
    """
    
    def __init__(self, db: Session):
        """
        Initialize the template service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_by_id(self, template_id: UUID) -> Optional[Template]:
        """Get a template by ID."""
        return self.db.query(Template).filter(Template.id == template_id).first()
    
    def get_system_templates(self) -> List[Template]:
        """
        Get all system templates.
        
        System templates are created by admins and available to all users.
        """
        return self.db.query(Template).filter(
            Template.is_system == True
        ).order_by(Template.name).all()
    
    def get_user_templates(self, user_id: UUID) -> List[Template]:
        """
        Get all personal templates for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of user's personal templates
        """
        return self.db.query(Template).filter(
            and_(
                Template.user_id == user_id,
                Template.is_system == False,
            )
        ).order_by(Template.updated_at.desc()).all()
    
    def get_accessible_templates(
        self,
        user_id: UUID,
        category: Optional[TemplateCategory] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Template], int]:
        """
        Get all templates accessible to a user.
        
        This includes:
        - System templates
        - User's personal templates
        - Public templates from other users
        
        Args:
            user_id: User's UUID
            category: Filter by category
            platform: Filter by target platform
            search: Search in name and description
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (templates list, total count)
        """
        # Base query: system templates OR user's templates OR public templates
        query = self.db.query(Template).filter(
            or_(
                Template.is_system == True,
                Template.user_id == user_id,
                Template.is_public == True,
            )
        )
        
        # Apply filters
        if category:
            query = query.filter(Template.category == category)
        
        if platform:
            query = query.filter(Template.target_platforms.contains([platform]))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Template.name.ilike(search_term),
                    Template.description.ilike(search_term),
                )
            )
        
        # Get total count
        total = query.count()
        
        # Order: system templates first, then by updated_at
        query = query.order_by(
            Template.is_system.desc(),
            Template.updated_at.desc(),
        )
        
        # Apply pagination
        templates = query.offset(skip).limit(limit).all()
        
        return templates, total
    
    def can_access_template(self, template: Template, user_id: UUID) -> bool:
        """
        Check if a user can access a template.
        
        Args:
            template: Template to check
            user_id: User's UUID
            
        Returns:
            True if user can access the template
        """
        # System templates are accessible to all
        if template.is_system:
            return True
        
        # User's own templates
        if template.user_id == user_id:
            return True
        
        # Public templates
        if template.is_public:
            return True
        
        return False
    
    def can_edit_template(self, template: Template, user: User) -> bool:
        """
        Check if a user can edit a template.
        
        Args:
            template: Template to check
            user: User attempting to edit
            
        Returns:
            True if user can edit the template
        """
        # Admins can edit system templates
        if template.is_system:
            return user.role == UserRole.ADMIN
        
        # Users can only edit their own templates
        return template.user_id == user.id
    
    # =========================================================================
    # Create/Update Methods
    # =========================================================================
    
    def create_template(
        self,
        user_id: Optional[UUID],
        name: str,
        description: Optional[str] = None,
        category: TemplateCategory = TemplateCategory.GENERAL,
        is_system: bool = False,
        is_public: bool = False,
        **config_kwargs,
    ) -> Template:
        """
        Create a new template.
        
        Args:
            user_id: Owner's UUID (None for system templates)
            name: Template name
            description: Template description
            category: Template category
            is_system: Whether this is a system template
            is_public: Whether this template is public
            **config_kwargs: Additional template configuration
            
        Returns:
            Newly created Template instance
        """
        template = Template(
            user_id=user_id,
            name=name,
            description=description,
            category=category,
            is_system=is_system,
            is_public=is_public,
            **config_kwargs,
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Created template: {template.name} (id={template.id})")
        return template
    
    def update_template(
        self,
        template: Template,
        **update_kwargs,
    ) -> Template:
        """
        Update a template's configuration.
        
        Args:
            template: Template to update
            **update_kwargs: Fields to update
            
        Returns:
            Updated Template instance
        """
        # Update provided fields
        for key, value in update_kwargs.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)
        
        # Increment version
        template.version += 1
        
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Updated template: {template.name} (v{template.version})")
        return template
    
    def delete_template(self, template: Template) -> None:
        """
        Delete a template.
        
        Args:
            template: Template to delete
        """
        template_id = template.id
        template_name = template.name
        
        self.db.delete(template)
        self.db.commit()
        
        logger.info(f"Deleted template: {template_name} (id={template_id})")
    
    def duplicate_template(
        self,
        template: Template,
        new_owner_id: UUID,
        new_name: Optional[str] = None,
    ) -> Template:
        """
        Duplicate a template for a user.
        
        Creates a personal copy of a template (system or another user's public template).
        
        Args:
            template: Template to duplicate
            new_owner_id: UUID of the new owner
            new_name: New name for the duplicate (optional)
            
        Returns:
            Newly created Template instance
        """
        # Create a copy of the template data
        new_template = Template(
            user_id=new_owner_id,
            name=new_name or f"{template.name} (Copy)",
            description=template.description,
            category=template.category,
            target_platforms=template.target_platforms.copy() if template.target_platforms else [],
            tags=template.tags.copy() if template.tags else [],
            
            # Video Structure
            hook_style=template.hook_style,
            narrative_structure=template.narrative_structure,
            num_scenes=template.num_scenes,
            duration_min=template.duration_min,
            duration_max=template.duration_max,
            pacing=template.pacing,
            
            # Visual Style
            aspect_ratio=template.aspect_ratio,
            color_palette=copy.deepcopy(template.color_palette) if template.color_palette else {},
            visual_aesthetic=template.visual_aesthetic,
            transitions=template.transitions,
            filter_mood=template.filter_mood,
            
            # Text & Captions
            caption_style=template.caption_style,
            font_style=template.font_style,
            text_position=template.text_position,
            hook_text_overlay=template.hook_text_overlay,
            
            # Audio
            voice_gender=template.voice_gender,
            voice_tone=template.voice_tone,
            voice_speed=template.voice_speed,
            music_mood=template.music_mood,
            sound_effects=template.sound_effects,
            
            # Script/Prompt
            script_structure_prompt=template.script_structure_prompt,
            tone_instructions=template.tone_instructions,
            cta_type=template.cta_type,
            cta_placement=template.cta_placement,
            
            # Platform Optimization
            thumbnail_style=template.thumbnail_style,
            suggested_hashtags=template.suggested_hashtags.copy() if template.suggested_hashtags else [],
            
            # Ownership
            is_system=False,
            is_public=False,
            version=1,
        )
        
        self.db.add(new_template)
        self.db.commit()
        self.db.refresh(new_template)
        
        logger.info(
            f"Duplicated template: {template.name} -> {new_template.name} "
            f"for user {new_owner_id}"
        )
        return new_template
    
    # =========================================================================
    # Template Configuration
    # =========================================================================
    
    def get_template_config(self, template: Template) -> Dict[str, Any]:
        """
        Get the full configuration for a template.
        
        This returns a dictionary suitable for passing to the
        video generation pipeline.
        
        Args:
            template: Template to export
            
        Returns:
            Dictionary with full template configuration
        """
        return template.to_config_dict()
    
    def apply_config_to_template(
        self,
        template: Template,
        config: Dict[str, Any],
    ) -> Template:
        """
        Apply a configuration dictionary to a template.
        
        Args:
            template: Template to update
            config: Configuration dictionary
            
        Returns:
            Updated Template instance
        """
        # Video structure
        video_structure = config.get("video_structure", {})
        if video_structure:
            if "hook_style" in video_structure:
                template.hook_style = HookStyle(video_structure["hook_style"])
            if "narrative_structure" in video_structure:
                template.narrative_structure = NarrativeStructure(video_structure["narrative_structure"])
            if "num_scenes" in video_structure:
                template.num_scenes = video_structure["num_scenes"]
            if "duration_range" in video_structure:
                template.duration_min = video_structure["duration_range"].get("min", template.duration_min)
                template.duration_max = video_structure["duration_range"].get("max", template.duration_max)
            if "pacing" in video_structure:
                template.pacing = Pacing(video_structure["pacing"])
        
        # Visual style
        visual_style = config.get("visual_style", {})
        if visual_style:
            if "aspect_ratio" in visual_style:
                template.aspect_ratio = AspectRatio(visual_style["aspect_ratio"])
            if "color_palette" in visual_style:
                template.color_palette = visual_style["color_palette"]
            if "visual_aesthetic" in visual_style:
                template.visual_aesthetic = VisualAesthetic(visual_style["visual_aesthetic"])
            if "transitions" in visual_style:
                template.transitions = visual_style["transitions"]
            if "filter_mood" in visual_style:
                template.filter_mood = visual_style["filter_mood"]
        
        # Audio
        audio = config.get("audio", {})
        if audio:
            if "voice_gender" in audio:
                template.voice_gender = audio["voice_gender"]
            if "voice_tone" in audio:
                template.voice_tone = VoiceTone(audio["voice_tone"])
            if "voice_speed" in audio:
                template.voice_speed = audio["voice_speed"]
            if "music_mood" in audio:
                template.music_mood = MusicMood(audio["music_mood"])
            if "sound_effects" in audio:
                template.sound_effects = audio["sound_effects"]
        
        # Script prompt
        script_prompt = config.get("script_prompt", {})
        if script_prompt:
            if "structure_prompt" in script_prompt:
                template.script_structure_prompt = script_prompt["structure_prompt"]
            if "tone_instructions" in script_prompt:
                template.tone_instructions = script_prompt["tone_instructions"]
            if "cta_type" in script_prompt:
                template.cta_type = CTAType(script_prompt["cta_type"])
            if "cta_placement" in script_prompt:
                template.cta_placement = script_prompt["cta_placement"]
        
        template.version += 1
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_template_stats(self) -> Dict[str, Any]:
        """
        Get platform-wide template statistics.
        
        Returns:
            Dictionary with template statistics
        """
        total = self.db.query(Template).count()
        system_count = self.db.query(Template).filter(Template.is_system == True).count()
        
        # Count by category
        by_category = {}
        for category in TemplateCategory:
            count = self.db.query(Template).filter(Template.category == category).count()
            by_category[category.value] = count
        
        return {
            "total": total,
            "system_templates": system_count,
            "user_templates": total - system_count,
            "by_category": by_category,
        }


def get_template_service(db: Session) -> TemplateService:
    """Factory function to create a TemplateService instance."""
    return TemplateService(db)

