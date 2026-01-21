"""
Admin API Endpoints

Endpoints for platform administration (admin only).
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_admin
from app.models.user import User, UserRole
from app.services.admin import AdminService
from app.schemas.admin import (
    AdminUserItem,
    AdminUserListResponse,
    AdminUserDetailResponse,
    AdminUserStats,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    DeleteUserRequest,
    PlatformStatsResponse,
    UserStats,
    VideoStats,
    PostStats,
    SubscriptionStats,
    ActivityStatsResponse,
    DailyDataPoint,
    TopUsersResponse,
    TopUserItem,
    SettingsResponse,
    SetSettingRequest,
    SettingItem,
    TemplateStatsResponse,
    TemplateUsageItem,
    RecentVideoItem,
    RecentPostItem,
    FailedJobItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# User Management
# =============================================================================

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = Query(default=None, description="Search by email or name"),
    role: Optional[str] = Query(default=None, description="Filter by role"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users with filtering and pagination.
    """
    service = AdminService(db)
    
    # Parse role if provided
    role_filter = None
    if role:
        try:
            role_filter = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}",
            )
    
    result = service.get_users(
        search=search,
        role=role_filter,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    
    return AdminUserListResponse(
        users=[
            AdminUserItem(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                role=u.role.value,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login=u.last_login,
            )
            for u in result["users"]
        ],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        has_more=result["has_more"],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific user.
    """
    service = AdminService(db)
    result = service.get_user_details(user_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user = result["user"]
    subscription = result["subscription"]
    
    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        subscription_status=subscription.status.value if subscription else None,
        subscription_plan=subscription.plan.value if subscription and subscription.plan else None,
        stats=AdminUserStats(**result["stats"]),
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's role.
    """
    # Prevent self-demotion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    
    # Validate role
    try:
        new_role = UserRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}",
        )
    
    service = AdminService(db)
    user = service.update_user_role(user_id, new_role)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {
        "message": f"User role updated to {new_role.value}",
        "user_id": str(user_id),
        "new_role": new_role.value,
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Enable or disable a user account.
    """
    # Prevent self-disabling
    if user_id == current_user.id and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )
    
    service = AdminService(db)
    user = service.update_user_status(user_id, request.is_active)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    action = "enabled" if request.is_active else "disabled"
    return {
        "message": f"User account {action}",
        "user_id": str(user_id),
        "is_active": request.is_active,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    hard_delete: bool = Query(default=False, description="Permanently delete"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a user account.
    
    By default, performs a soft delete. Set hard_delete=true to permanently delete.
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    service = AdminService(db)
    success = service.delete_user(user_id, hard_delete=hard_delete)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    delete_type = "permanently deleted" if hard_delete else "disabled"
    return {
        "message": f"User {delete_type}",
        "user_id": str(user_id),
    }


# =============================================================================
# Platform Statistics
# =============================================================================

@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide statistics.
    """
    service = AdminService(db)
    stats = service.get_platform_stats()
    
    return PlatformStatsResponse(
        users=UserStats(**stats["users"]),
        videos=VideoStats(**stats["videos"]),
        posts=PostStats(**stats["posts"]),
        subscriptions=SubscriptionStats(**stats["subscriptions"]),
    )


@router.get("/stats/activity", response_model=ActivityStatsResponse)
async def get_activity_stats(
    days: int = Query(default=30, ge=7, le=365, description="Number of days"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get activity statistics over time.
    """
    service = AdminService(db)
    stats = service.get_activity_stats(days)
    
    return ActivityStatsResponse(
        period_days=stats["period_days"],
        daily_signups=[DailyDataPoint(**d) for d in stats["daily_signups"]],
        daily_videos=[DailyDataPoint(**d) for d in stats["daily_videos"]],
        daily_posts=[DailyDataPoint(**d) for d in stats["daily_posts"]],
    )


@router.get("/stats/top-users", response_model=TopUsersResponse)
async def get_top_users(
    metric: str = Query(default="videos", description="Metric (videos, posts)"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of users"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get top users by a specific metric.
    """
    service = AdminService(db)
    users = service.get_top_users(metric, limit)
    
    return TopUsersResponse(
        metric=metric,
        users=[TopUserItem(**u) for u in users],
    )


@router.get("/stats/templates", response_model=TemplateStatsResponse)
async def get_template_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get template usage statistics.
    """
    service = AdminService(db)
    stats = service.get_template_stats()
    
    return TemplateStatsResponse(
        total=stats["total"],
        system=stats["system"],
        user_created=stats["user_created"],
        most_used=[TemplateUsageItem(**t) for t in stats["most_used"]],
    )


# =============================================================================
# System Settings
# =============================================================================

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get all application settings.
    """
    service = AdminService(db)
    settings = service.get_app_settings()
    
    return SettingsResponse(settings=settings)


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific setting.
    """
    service = AdminService(db)
    value = service.get_setting(key)
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting not found: {key}",
        )
    
    return {"key": key, "value": value}


@router.post("/settings")
async def set_setting(
    request: SetSettingRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Set an application setting.
    """
    service = AdminService(db)
    setting = service.set_setting(
        key=request.key,
        value=request.value,
        description=request.description,
    )
    
    return {
        "message": "Setting updated",
        "key": setting.key,
        "value": setting.value,
    }


@router.delete("/settings/{key}")
async def delete_setting(
    key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete an application setting.
    """
    service = AdminService(db)
    success = service.delete_setting(key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting not found: {key}",
        )
    
    return {"message": f"Setting '{key}' deleted"}


# =============================================================================
# Content Management
# =============================================================================

@router.get("/content/videos")
async def get_recent_videos(
    limit: int = Query(default=20, ge=1, le=100, description="Number of videos"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get recently created videos.
    """
    service = AdminService(db)
    videos = service.get_recent_videos(limit)
    
    # Get user emails
    user_ids = [v.user_id for v in videos]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.email for u in users}
    
    return {
        "videos": [
            RecentVideoItem(
                id=v.id,
                title=v.title,
                status=v.status.value,
                user_id=v.user_id,
                user_email=user_map.get(v.user_id),
                created_at=v.created_at,
            )
            for v in videos
        ]
    }


@router.get("/content/posts")
async def get_recent_posts(
    limit: int = Query(default=20, ge=1, le=100, description="Number of posts"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get recently created posts.
    """
    service = AdminService(db)
    posts = service.get_recent_posts(limit)
    
    # Get user emails
    user_ids = [p.user_id for p in posts]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.email for u in users}
    
    return {
        "posts": [
            RecentPostItem(
                id=p.id,
                title=p.title,
                status=p.status.value,
                platforms=p.platforms or [],
                user_id=p.user_id,
                user_email=user_map.get(p.user_id),
                created_at=p.created_at,
            )
            for p in posts
        ]
    }


@router.get("/content/failed-jobs")
async def get_failed_jobs(
    limit: int = Query(default=50, ge=1, le=100, description="Number of jobs"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get recently failed jobs.
    """
    service = AdminService(db)
    jobs = service.get_failed_jobs(limit)
    
    return {
        "jobs": [
            FailedJobItem(
                id=j.id,
                job_type=j.job_type,
                error_message=j.error_message,
                user_id=j.user_id,
                created_at=j.created_at,
            )
            for j in jobs
        ]
    }
