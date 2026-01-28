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
# Stuck Videos Management (must be before /{video_id} routes)
# =============================================================================

@router.get("/stuck", response_model=dict)
async def get_stuck_videos(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get videos that appear to be stuck (pending/processing for > 30 minutes).
    
    **Requires:** Authentication
    """
    video_service = VideoService(db)
    stuck = video_service.get_stuck_videos(user.id)
    active = video_service.get_active_generation(user.id)
    
    return {
        "stuck_videos": [
            {
                "id": str(v.id),
                "title": v.title,
                "status": v.status,
                "created_at": str(v.created_at),
                "updated_at": str(v.updated_at),
            }
            for v in stuck
        ],
        "stuck_count": len(stuck),
        "has_active_generation": active is not None,
        "active_video_id": str(active.id) if active else None,
    }


@router.post("/stuck/clear", response_model=dict)
async def clear_stuck_videos(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Clear stuck videos by marking them as failed.
    This unblocks new video generation.
    
    **Requires:** Authentication
    """
    video_service = VideoService(db)
    cleared_count = video_service.clear_stuck_videos(user.id)
    
    return {
        "cleared_count": cleared_count,
        "message": f"Cleared {cleared_count} stuck video(s)",
    }


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
# Scheduled Videos
# =============================================================================

@router.get("/scheduled", response_model=dict)
async def list_scheduled_videos(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List scheduled/planned videos for the current user.
    
    Returns videos with planning_status in: planned, generating, ready
    
    **Requires:** Authentication
    """
    from app.models.video import PlanningStatus
    
    video_service = VideoService(db)
    
    # Get videos in planning workflow
    videos = db.query(Video).filter(
        Video.user_id == user.id,
        Video.planning_status.in_([
            PlanningStatus.PLANNED.value,
            PlanningStatus.GENERATING.value,
            PlanningStatus.READY.value,
        ])
    ).order_by(Video.scheduled_post_time.asc()).offset(skip).limit(limit).all()
    
    total = db.query(Video).filter(
        Video.user_id == user.id,
        Video.planning_status.in_([
            PlanningStatus.PLANNED.value,
            PlanningStatus.GENERATING.value,
            PlanningStatus.READY.value,
        ])
    ).count()
    
    return {
        "videos": [_video_to_response(v) for v in videos],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# =============================================================================
# Generate Now (for scheduled videos)
# =============================================================================

@router.post("/{video_id}/generate-now", response_model=dict)
async def generate_video_now(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Trigger immediate generation for a scheduled video.
    
    Can be used to generate a video before its scheduled time.
    
    **Path Parameters:**
    - `video_id`: UUID of the scheduled video
    
    **Requires:** Authentication (must own the video)
    """
    from app.models.video import PlanningStatus
    from app.workers.video_scheduler import queue_video_generation
    from datetime import datetime
    
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
            detail="Not authorized to access this video",
        )
    
    # Check if video is in planned status
    if video.planning_status != PlanningStatus.PLANNED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate video in status: {video.planning_status}",
        )
    
    # Check concurrent generation limit
    active = video_service.get_active_generation(user.id)
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a video generating. Please wait for it to complete.",
        )
    
    # Trigger generation
    video.planning_status = PlanningStatus.GENERATING.value
    video.generation_triggered_at = datetime.utcnow()
    db.commit()
    
    job_id = queue_video_generation(
        video_id=str(video.id),
        user_id=str(video.user_id),
        ai_suggestion_data=video.ai_suggestion_data,
    )
    
    return {
        "success": True,
        "video_id": str(video.id),
        "message": "Video generation triggered",
        "job_id": job_id,
    }


# =============================================================================
# Cancel Video
# =============================================================================

@router.post("/{video_id}/cancel", response_model=dict)
async def cancel_video(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a video generation in progress.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Authentication (must own the video)
    """
    from app.models.video import PlanningStatus
    
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
            detail="Not authorized to cancel this video",
        )
    
    # Check if video can be cancelled
    cancellable_statuses = ["pending", "processing"]
    if video.status not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel video in status: {video.status}",
        )
    
    # Cancel the video
    video.status = VideoStatus.CANCELLED.value
    video.error_message = "Cancelled by user"
    
    if video.planning_status == PlanningStatus.GENERATING.value:
        video.planning_status = PlanningStatus.FAILED.value
    
    db.commit()
    
    return {
        "success": True,
        "video_id": str(video.id),
        "message": "Video generation cancelled",
    }


# =============================================================================
# Reschedule Video
# =============================================================================

@router.put("/{video_id}/reschedule", response_model=dict)
async def reschedule_video(
    video_id: UUID,
    scheduled_post_time: datetime = Query(..., description="New scheduled time"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reschedule a planned video.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Query Parameters:**
    - `scheduled_post_time`: New scheduled post time
    
    **Requires:** Authentication (must own the video), Premium for scheduling
    """
    from app.models.video import PlanningStatus
    
    # Check premium for scheduling
    if not user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scheduling requires a premium subscription",
        )
    
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
            detail="Not authorized to reschedule this video",
        )
    
    # Can only reschedule planned videos
    if video.planning_status != PlanningStatus.PLANNED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule video in status: {video.planning_status}",
        )
    
    # Validate new time is in the future
    if scheduled_post_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future",
        )
    
    # Update scheduled time
    video.scheduled_post_time = scheduled_post_time
    video.generation_triggered_at = None  # Reset trigger
    db.commit()
    
    return {
        "success": True,
        "video_id": str(video.id),
        "new_scheduled_time": scheduled_post_time.isoformat(),
        "message": "Video rescheduled",
    }


# =============================================================================
# Edit Planned Video
# =============================================================================

@router.put("/{video_id}/edit", response_model=VideoResponse)
async def edit_planned_video(
    video_id: UUID,
    title: Optional[str] = Query(None),
    prompt: Optional[str] = Query(None),
    template_id: Optional[UUID] = Query(None),
    target_platforms: Optional[List[str]] = Query(None),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Edit a planned video's details.
    
    Can only edit videos that haven't started generation yet.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Query Parameters:**
    - `title`: New title (optional)
    - `prompt`: New prompt (optional)
    - `template_id`: New template ID (optional)
    - `target_platforms`: New target platforms (optional)
    
    **Requires:** Authentication (must own the video)
    """
    from app.models.video import PlanningStatus
    
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
            detail="Not authorized to edit this video",
        )
    
    # Can only edit planned videos
    if video.planning_status != PlanningStatus.PLANNED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit video in status: {video.planning_status}",
        )
    
    # Apply updates
    if title is not None:
        video.title = title
    
    if prompt is not None:
        video.prompt = prompt
        # Also update in ai_suggestion_data if present
        if video.ai_suggestion_data:
            video.ai_suggestion_data["prompt"] = prompt
    
    if template_id is not None:
        # Validate template
        template_service = TemplateService(db)
        template = template_service.get_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )
        video.template_id = template_id
    
    if target_platforms is not None:
        video.target_platforms = target_platforms
    
    db.commit()
    db.refresh(video)
    
    return _video_to_response(video)


# =============================================================================
# Download Video
# =============================================================================

@router.get("/{video_id}/download")
async def download_video(
    video_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get download URL for a video.
    
    Redirects to the video URL (GCS) or returns an error if video
    is not available for download.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Authentication (must own the video)
    """
    from fastapi.responses import RedirectResponse
    
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
            detail="Not authorized to download this video",
        )
    
    # Check if video is completed
    if video.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video is not ready for download. Status: {video.status}",
        )
    
    # Check if video URL exists
    if not video.video_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not available",
        )
    
    # Check if it's a cloud URL
    if video.video_url.startswith("file://"):
        # Local file - not accessible via HTTP
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video is stored locally and cannot be downloaded. Please configure cloud storage (GCS).",
        )
    
    # Redirect to the video URL (GCS public URL)
    logger.info(f"Redirecting to video URL: {video.video_url}")
    return RedirectResponse(url=video.video_url, status_code=302)


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
        # Planning fields
        planning_status=video.planning_status,
        scheduled_post_time=video.scheduled_post_time,
        generation_triggered_at=video.generation_triggered_at,
        posted_at=video.posted_at,
        series_name=video.series_name,
        series_order=video.series_order,
        target_platforms=video.target_platforms,
        ai_suggestion_data=video.ai_suggestion_data,
    )
