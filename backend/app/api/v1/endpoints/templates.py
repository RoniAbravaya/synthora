"""
Template Management API Endpoints

Handles video generation templates (system and personal).
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_admin
from app.models.user import User
from app.models.template import Template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


# =============================================================================
# Response Models (inline for simplicity)
# =============================================================================

def template_to_response(template: Template) -> Dict[str, Any]:
    """Convert a Template model to frontend-compatible response."""
    return template.to_frontend_format()


# =============================================================================
# List Templates
# =============================================================================

@router.get("")
async def list_templates(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search in name and description"),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=100, description="Records to return"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all accessible templates.
    
    Returns:
    - System templates (user_id is NULL)
    - User's personal templates
    - Public templates from other users
    """
    # Base query: system templates OR user's templates OR public templates
    query = db.query(Template).filter(
        or_(
            Template.user_id == None,  # System templates
            Template.user_id == user.id,  # User's own templates
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
        Template.user_id.is_(None).desc(),  # NULL (system) first
        Template.name
    )
    
    # Apply pagination
    templates = query.offset(skip).limit(limit).all()
    
    return {
        "templates": [template_to_response(t) for t in templates],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/system")
async def list_system_templates(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all system templates.
    
    System templates are templates with user_id=NULL.
    """
    templates = db.query(Template).filter(
        Template.user_id == None
    ).order_by(Template.name).all()
    
    return {
        "templates": [template_to_response(t) for t in templates],
        "total": len(templates),
    }


@router.get("/my")
async def list_my_templates(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List the current user's personal templates.
    """
    templates = db.query(Template).filter(
        Template.user_id == user.id
    ).order_by(Template.name).all()
    
    return {
        "templates": [template_to_response(t) for t in templates],
        "total": len(templates),
    }


# =============================================================================
# Get Single Template
# =============================================================================

@router.get("/{template_id}")
async def get_template(
    template_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a template by ID.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check access
    can_access = (
        template.user_id is None or  # System template
        template.user_id == user.id or  # User's own
        template.is_public  # Public template
    )
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this template",
        )
    
    return template_to_response(template)


# =============================================================================
# Create Template
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(
    data: Dict[str, Any],
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal template.
    """
    # Extract data
    name = data.get("name", "Untitled Template")
    description = data.get("description")
    category = data.get("category", "general")
    is_public = data.get("is_public", False)
    config = data.get("config", {})
    tags = data.get("tags", [])
    
    # Create template
    template = Template(
        user_id=user.id,
        name=name,
        description=description,
        category=category,
        is_public=is_public,
        config=config,
        tags=tags,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template_to_response(template)


# =============================================================================
# Update Template
# =============================================================================

@router.patch("/{template_id}")
async def update_template(
    template_id: UUID,
    data: Dict[str, Any],
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a template.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check edit access
    can_edit = (
        (template.user_id is None and user.is_admin) or  # Admin can edit system
        template.user_id == user.id  # User can edit own
    )
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this template",
        )
    
    # Update fields
    if "name" in data:
        template.name = data["name"]
    if "description" in data:
        template.description = data["description"]
    if "category" in data:
        template.category = data["category"]
    if "is_public" in data:
        template.is_public = data["is_public"]
    if "config" in data:
        template.config = data["config"]
    if "tags" in data:
        template.tags = data["tags"]
    
    db.commit()
    db.refresh(template)
    
    return template_to_response(template)


# =============================================================================
# Delete Template
# =============================================================================

@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a template.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check delete access
    can_delete = (
        (template.user_id is None and user.is_admin) or  # Admin can delete system
        template.user_id == user.id  # User can delete own
    )
    
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this template",
        )
    
    template_name = template.name
    db.delete(template)
    db.commit()
    
    return {"message": f"Template '{template_name}' deleted"}


# =============================================================================
# Duplicate Template
# =============================================================================

@router.post("/{template_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_template(
    template_id: UUID,
    data: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Duplicate a template.
    
    Creates a personal copy of a template.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check access
    can_access = (
        template.user_id is None or  # System template
        template.user_id == user.id or  # User's own
        template.is_public  # Public template
    )
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this template",
        )
    
    # Get new name
    new_name = template.name + " (Copy)"
    if data and "name" in data:
        new_name = data["name"]
    
    # Create copy
    new_template = Template(
        user_id=user.id,
        name=new_name,
        description=template.description,
        category=template.category,
        is_public=False,
        config=template.config.copy() if template.config else {},
        tags=template.tags.copy() if template.tags else [],
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return template_to_response(new_template)


# =============================================================================
# Categories
# =============================================================================

@router.get("/categories")
async def get_categories():
    """
    Get available template categories.
    """
    return {
        "categories": [
            "educational",
            "entertainment",
            "product",
            "motivational",
            "news",
            "howto",
            "lifestyle",
            "general",
        ]
    }
