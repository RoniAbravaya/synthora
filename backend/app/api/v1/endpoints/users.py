"""
User Management API Endpoints

Handles user profile operations and admin user management.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import (
    get_current_active_user,
    require_admin,
)
from app.services.user import UserService
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse,
    UserProfileResponse,
    UserUpdate,
    RoleUpdate,
    StatusUpdate,
    UserListResponse,
    UserStatsResponse,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# User Profile Endpoints (Self)
# =============================================================================

@router.get("/profile", response_model=UserProfileResponse)
async def get_my_profile(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's profile.
    
    Returns comprehensive profile information including subscription
    status and feature access.
    
    **Requires:** Authentication
    """
    user_service = UserService(db)
    profile_data = user_service.get_user_profile_data(user)
    
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        **profile_data,
    )


@router.patch("/profile", response_model=UserResponse)
async def update_my_profile(
    update: UserUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    
    **Request Body:**
    - `name`: New display name (optional)
    - `avatar_url`: New avatar URL (optional)
    
    **Requires:** Authentication
    """
    user_service = UserService(db)
    updated_user = user_service.update_user(
        user,
        name=update.name,
        avatar_url=update.avatar_url,
    )
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        name=updated_user.name,
        avatar_url=updated_user.avatar_url,
        role=updated_user.role,
        is_active=updated_user.is_active,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )


# =============================================================================
# Admin User Management Endpoints
# =============================================================================

@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Records to return"),
    role: Optional[UserRole] = Query(default=None, description="Filter by role"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    search: Optional[str] = Query(default=None, description="Search by email or name"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users with optional filtering.
    
    **Query Parameters:**
    - `skip`: Number of records to skip (pagination)
    - `limit`: Maximum records to return (1-100)
    - `role`: Filter by user role (admin, premium, free)
    - `is_active`: Filter by active status
    - `search`: Search by email or name
    
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
    
    user_responses = [
        UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            avatar_url=u.avatar_url,
            role=u.role,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]
    
    return UserListResponse(
        users=user_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide user statistics.
    
    Returns:
    - Total user count
    - Users by role
    - Active user count
    - New users this month
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    stats = user_service.get_user_stats()
    
    return UserStatsResponse(
        total_users=stats["total"],
        by_role=stats["by_role"],
        active_users=stats["active"],
        new_this_month=stats["new_this_month"],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    update: RoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's role.
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Request Body:**
    - `role`: New role (admin, premium, free)
    
    **Requires:** Admin role
    
    **Note:** Admins cannot change their own role to prevent lockout.
    """
    # Prevent admin from demoting themselves
    if user_id == admin.id and update.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )
    
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    updated_user = user_service.update_role(user, update.role)
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        name=updated_user.name,
        avatar_url=updated_user.avatar_url,
        role=updated_user.role,
        is_active=updated_user.is_active,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: UUID,
    update: StatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Enable or disable a user account.
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Request Body:**
    - `is_active`: Whether the account should be active
    
    **Requires:** Admin role
    
    **Note:** Admins cannot disable their own account.
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
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        name=updated_user.name,
        avatar_url=updated_user.avatar_url,
        role=updated_user.role,
        is_active=updated_user.is_active,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )


@router.post("/{user_id}/grant-premium", response_model=MessageResponse)
async def grant_premium(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Grant premium access to a user (without Stripe subscription).
    
    This is useful for:
    - Giving free premium access to beta testers
    - Compensating users for issues
    - Internal/partner accounts
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Requires:** Admin role
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.role == UserRole.ADMIN:
        return MessageResponse(message="User is already an admin with full access")
    
    if user.role == UserRole.PREMIUM:
        return MessageResponse(message="User already has premium access")
    
    user_service.update_role(user, UserRole.PREMIUM)
    
    return MessageResponse(message=f"Premium access granted to {user.email}")


@router.post("/{user_id}/revoke-premium", response_model=MessageResponse)
async def revoke_premium(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Revoke premium access from a user.
    
    This downgrades the user to the free tier.
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Requires:** Admin role
    
    **Note:** Cannot revoke admin access through this endpoint.
    """
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke admin access through this endpoint",
        )
    
    if user.role == UserRole.FREE:
        return MessageResponse(message="User is already on the free tier")
    
    user_service.update_role(user, UserRole.FREE)
    
    return MessageResponse(message=f"Premium access revoked from {user.email}")
