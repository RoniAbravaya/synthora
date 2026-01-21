"""
User Management API Endpoints

Handles user profile operations and admin user management.
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import (
    get_current_active_user,
    require_admin,
)
from app.services.user import UserService
from app.models.user import User
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# Helper Functions
# =============================================================================

def user_to_response(user: User) -> Dict[str, Any]:
    """Convert user to response format."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": str(user.created_at) if user.created_at else None,
        "updated_at": str(user.updated_at) if user.updated_at else None,
    }


# =============================================================================
# Request Models
# =============================================================================

class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    role: str  # "admin", "premium", "free"


class StatusUpdateRequest(BaseModel):
    is_active: bool


class BootstrapAdminRequest(BaseModel):
    email: str


# =============================================================================
# User Profile Endpoints (Self)
# =============================================================================

@router.get("/profile")
async def get_my_profile(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's profile.
    """
    user_service = UserService(db)
    profile_data = user_service.get_user_profile_data(user)
    
    response = user_to_response(user)
    response.update(profile_data)
    return response


@router.patch("/profile")
async def update_my_profile(
    update: UserUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    """
    user_service = UserService(db)
    updated_user = user_service.update_user(
        user,
        display_name=update.display_name,
        photo_url=update.photo_url,
    )
    
    return user_to_response(updated_user)


# =============================================================================
# Bootstrap Admin Endpoint (No Auth Required)
# =============================================================================

@router.post("/bootstrap-admin")
async def bootstrap_admin(
    request: BootstrapAdminRequest,
    db: Session = Depends(get_db),
):
    """
    Bootstrap admin endpoint - make a user admin by email.
    
    This endpoint only works if NO admin exists yet (first-time setup).
    
    **Request Body:**
    - `email`: Email of the user to make admin
    
    **Note:** This endpoint does not require authentication.
    """
    user_service = UserService(db)
    
    # Check if admin already exists
    if user_service.admin_exists():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An admin already exists. Use admin panel to manage roles.",
        )
    
    # Find the user
    user = user_service.get_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {request.email} not found. Please log in first.",
        )
    
    # Make them admin
    updated_user = user_service.update_role(user, "admin")
    
    logger.info(f"Bootstrap admin created: {request.email}")
    
    return {
        "message": f"User {request.email} is now an admin",
        "user": user_to_response(updated_user),
    }


# =============================================================================
# Admin User Management Endpoints
# =============================================================================

@router.get("")
async def list_users(
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Records to return"),
    role: Optional[str] = Query(default=None, description="Filter by role"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    search: Optional[str] = Query(default=None, description="Search by email or name"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users with optional filtering.
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    users, total = user_service.get_all(
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
        search=search,
    )
    
    return {
        "users": [user_to_response(u) for u in users],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats")
async def get_user_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide user statistics.
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    stats = user_service.get_user_stats()
    
    return {
        "total_users": stats["total"],
        "by_role": stats["by_role"],
        "active_users": stats["active"],
        "new_this_month": stats["new_this_month"],
    }


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user_to_response(user)


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    update: RoleUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's role.
    
    **Requires:** Admin role
    """
    # Prevent admin from demoting themselves
    if user_id == admin.id and update.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )
    
    # Validate role
    if update.role not in ["admin", "premium", "free"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {update.role}. Must be admin, premium, or free.",
        )
    
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    updated_user = user_service.update_role(user, update.role)
    
    return {
        "message": f"User role updated to {update.role}",
        "user": user_to_response(updated_user),
    }


@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    update: StatusUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Enable or disable a user account.
    
    **Requires:** Admin role
    """
    # Prevent admin from disabling themselves
    if user_id == admin.id and not update.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )
    
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    updated_user = user_service.set_active_status(user, update.is_active)
    
    return {
        "message": f"User {'enabled' if update.is_active else 'disabled'}",
        "user": user_to_response(updated_user),
    }


@router.post("/{user_id}/grant-premium", response_model=MessageResponse)
async def grant_premium(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Grant premium access to a user.
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.role == "admin":
        return MessageResponse(message="User is already an admin with full access")
    
    if user.role == "premium":
        return MessageResponse(message="User already has premium access")
    
    user_service.update_role(user, "premium")
    
    return MessageResponse(message=f"Premium access granted to {user.email}")


@router.post("/{user_id}/revoke-premium", response_model=MessageResponse)
async def revoke_premium(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Revoke premium access from a user.
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke admin access through this endpoint",
        )
    
    if user.role == "free":
        return MessageResponse(message="User is already on the free tier")
    
    user_service.update_role(user, "free")
    
    return MessageResponse(message=f"Premium access revoked from {user.email}")
