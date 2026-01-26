"""
Video Generation API Endpoints

Handles video generation, management, and status tracking.
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_premium, require_admin
from app.services.video import VideoService
from app.services.template import TemplateService
from app.services.integration import IntegrationService
from app.services.limits import LimitsService
from app.workers.scheduler import get_scheduler
from app.models.user import User, UserRole
from app.models.video import Video, VideoStatus, GenerationStep
from app.schemas.video import (
    VideoGenerateRequest,
    VideoResponse,
    VideoListResponse,
    VideoStatusResponse,
    VideoRetryRequest,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["Videos"])


# =============================================================================
# Daily Limit (must be before /{video_id} routes)
# =============================================================================

@router.get("/daily-limit", response_model=dict)
async def get_daily_limit(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the daily video generation limit for the current user.
    
    Returns:
        - limit: Maximum videos allowed per day (null for unlimited)
        - used: Videos created today
        - remaining: Videos remaining today (null for unlimited)
    
    **Requires:** Authentication
    """
    limits_service = LimitsService(db)
    return limits_service.get_video_limit_info(user.id)


# =============================================================================
# User Stats (must be before /{video_id} routes)
# =============================================================================

@router.get("/stats/me", response_model=dict)
async def get_my_video_stats(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get video statistics for the current user.
    
    **Requires:** Authentication
    """
    video_service = VideoService(db)
    return video_service.get_user_video_stats(user.id)


# =============================================================================
# Admin Endpoints (must be before /{video_id} routes)
# =============================================================================

@router.get("/admin/stats", response_model=dict)
async def get_platform_video_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide video statistics.
    
    **Requires:** Admin role
    """
    video_service = VideoService(db)
    return video_service.get_platform_video_stats()


# =============================================================================
# List Videos
# =============================================================================

@router.get("", response_model=VideoListResponse)
async def list_videos(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all videos for the current user.
    
    **Query Parameters:**
    - `status`: Filter by video status
    - `skip`: Pagination offset
    - `limit`: Maximum records to return
    
    **Requires:** Authentication
    """
    video_service = VideoService(db)
    
    videos, total = video_service.get_user_videos(
        user_id=user.id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    
    return VideoListResponse(
        videos=[_video_to_response(v) for v in videos],
        total=total,
        skip=skip,
        limit=limit,
    )


# =============================================================================
# Get Video
# =============================================================================

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a video by ID.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Authentication (must own the video)
    """
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    # Check ownership (admins can see any video)
    if video.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video",
        )
    
    return _video_to_response(video)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the generation status of a video.
    
    Use this endpoint for polling during video generation.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Authentication (must own the video)
    """
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    if video.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video",
        )
    
    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        progress=video.progress,
        current_step=video.current_step,
        generation_state=video.generation_config,
        error_message=video.error_message,
        error_details=None,  # Not stored as separate field
    )


# =============================================================================
# Generate Video
# =============================================================================

@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start a new video generation.
    
    **Request Body:**
    - `prompt`: Topic/prompt for the video (required)
    - `template_id`: Template to use (optional)
    - `title`: Video title (optional)
    - `config_overrides`: Configuration overrides (optional)
    
    **Requires:** Authentication
    
    **Limits:**
    - Free users: 1 video per day
    - Premium users: Unlimited
    - Max 1 concurrent generation per user
    """
    video_service = VideoService(db)
    integration_service = IntegrationService(db)
    limits_service = LimitsService(db)
    
    # Check daily limit
    can_generate, reason = limits_service.can_generate_video(user.id)
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )
    
    # Check concurrent generation limit
    active = video_service.get_active_generation(user.id)
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a video generating. Please wait for it to complete.",
        )
    
    # Check minimum integrations
    has_required, missing = integration_service.check_minimum_integrations(user.id)
    if not has_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required integrations: {', '.join(missing)}",
        )
    
    # Validate template if provided
    template_id = request.template_id
    if template_id:
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
                detail="Not authorized to use this template",
            )
    
    # Calculate expiration
    if user.role == UserRole.FREE:
        expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        expires_at = None  # Premium users: indefinite
    
    # Create video record
    video = video_service.create_video(
        user_id=user.id,
        prompt=request.prompt,
        template_id=template_id,
        title=request.title,
        expires_at=expires_at,
    )
    
    # Enqueue generation job
    scheduler = get_scheduler()
    scheduler.enqueue_video_generation(
        video_id=video.id,
        user_id=user.id,
        prompt=request.prompt,
        template_id=template_id,
        config_overrides=request.config_overrides,
    )
    
    return _video_to_response(video)


# =============================================================================
# Retry Video
# =============================================================================

@router.post("/{video_id}/retry", response_model=VideoResponse)
async def retry_video(
    video_id: UUID,
    request: VideoRetryRequest = None,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retry a failed video generation.
    
    Can optionally swap integrations for failed steps.
    
    **Path Parameters:**
    - `video_id`: UUID of the video to retry
    
    **Request Body (optional):**
    - `swap_integrations`: Map of step -> new provider
    
    **Requires:** Authentication (must own the video)
    """
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    if video.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to retry this video",
        )
    
    if video.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry video in status: {video.status}",
        )
    
    # Check concurrent limit
    active = video_service.get_active_generation(user.id)
    if active and active.id != video.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a video generating",
        )
    
    # Enqueue retry job
    scheduler = get_scheduler()
    swap_integrations = request.swap_integrations if request else None
    scheduler.enqueue_video_retry(
        video_id=video.id,
        swap_integration=swap_integrations,
    )
    
    # Update status
    video_service.update_status(video, "pending", progress=0)
    
    return _video_to_response(video)


# =============================================================================
# Delete Video
# =============================================================================

@router.delete("/{video_id}", response_model=MessageResponse)
async def delete_video(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a video.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Authentication (must own the video)
    """
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    if video.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this video",
        )
    
    # Allow deleting stuck videos - they may have failed silently
    # Only warn if video appears to be actively processing (recently updated)
    # But still allow deletion to clear stuck state
    
    video_service.delete_video(video)
    
    return MessageResponse(message="Video deleted")


# =============================================================================
# Helper Functions
# =============================================================================

def _video_to_response(video: Video) -> VideoResponse:
    """Convert a Video model to VideoResponse."""
    return VideoResponse(
        id=video.id,
        user_id=video.user_id,
        template_id=video.template_id,
        title=video.title,
        prompt=video.prompt,
        status=video.status,
        progress=video.progress,
        current_step=video.current_step,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        file_size=video.file_size,
        resolution=video.resolution,
        integrations_used=video.integrations_used or [],
        generation_time_seconds=video.generation_time_seconds,
        error_message=video.error_message,
        expires_at=video.expires_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )
