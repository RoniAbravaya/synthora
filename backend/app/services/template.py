"""
Template Service

Business logic for managing video generation templates.
Templates define the structure, style, and configuration for video generation.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
import copy

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.template import Template, TemplateCategory
from app.models.user import User

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
        
        System templates have user_id = NULL.
        """
        return self.db.query(Template).filter(
            Template.user_id == None
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
            Template.user_id == user_id
        ).order_by(Template.name).all()
    
    def get_accessible_templates(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Template], int]:
        """
        Get all templates accessible to a user.
        
        This includes:
        - System templates (user_id is NULL)
        - User's personal templates
        - Public templates from other users
        
        Args:
            user_id: User's UUID
            category: Filter by category
            search: Search in name and description
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (templates list, total count)
        """
        # Base query: system templates OR user's templates OR public templates
        query = self.db.query(Template).filter(
            or_(
                Template.user_id == None,  # System templates
                Template.user_id == user_id,  # User's templates
                Template.is_public == True,  # Public templates
            )
        )
        
        # Apply filters
        if category:
            query = query.filter(Template.category == category)
        
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
        
        # Order: system templates first (user_id is NULL), then by name
        query = query.order_by(
            Template.user_id.is_(None).desc(),
            Template.name,
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
        if template.user_id is None:
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
        if template.user_id is None:
            return user.is_admin
        
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
        category: str = "general",
        is_public: bool = False,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Template:
        """
        Create a new template.
        
        Args:
            user_id: Owner's UUID (None for system templates)
            name: Template name
            description: Template description
            category: Template category
            is_public: Whether this template is public
            config: Template configuration (JSONB)
            tags: Template tags
            
        Returns:
            Newly created Template instance
        """
        template = Template(
            user_id=user_id,
            name=name,
            description=description,
            category=category,
            is_public=is_public,
            config=config or {},
            tags=tags or [],
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
        
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Updated template: {template.name}")
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
        
        Creates a personal copy of a template.
        
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
            is_public=False,
            config=copy.deepcopy(template.config) if template.config else {},
            tags=template.tags.copy() if template.tags else [],
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
        
        Args:
            template: Template to export
            
        Returns:
            Dictionary with full template configuration
        """
        return template.config or {}
    
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
        system_count = self.db.query(Template).filter(Template.user_id == None).count()
        
        return {
            "total": total,
            "system_templates": system_count,
            "user_templates": total - system_count,
        }


def get_template_service(db: Session) -> TemplateService:
    """Factory function to create a TemplateService instance."""
    return TemplateService(db)
