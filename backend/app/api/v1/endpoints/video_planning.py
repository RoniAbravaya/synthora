"""
Video Planning API Endpoints

Endpoints for scheduling videos and creating content plans.
Supports single video scheduling, series creation, and monthly plans.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.auth import require_premium
from app.models.user import User
from app.models.video import Video, PlanningStatus
from app.services.video_planning import VideoPlanningService
from app.schemas.video_planning import (
    ScheduleVideoRequest,
    ScheduleVideoResponse,
    CreateSeriesRequest,
    CreateSeriesResponse,
    CreateMonthlyPlanRequest,
    CreateMonthlyPlanResponse,
    UpdatePlannedVideoRequest,
    PlannedVideoResponse,
    PlannedVideoListResponse,
    TriggerGenerationResponse,
    CalendarVideoItem,
    CalendarViewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-planning", tags=["Video Planning"])


# =============================================================================
# Helper Functions
# =============================================================================

def video_to_response(video: Video) -> PlannedVideoResponse:
    """Convert Video model to PlannedVideoResponse."""
    return PlannedVideoResponse(
        id=video.id,
        user_id=video.user_id,
        title=video.title,
        prompt=video.prompt,
        planning_status=video.planning_status or "none",
        scheduled_post_time=video.scheduled_post_time,
        generation_triggered_at=video.generation_triggered_at,
        posted_at=video.posted_at,
        series_name=video.series_name,
        series_order=video.series_order,
        target_platforms=video.target_platforms or [],
        ai_suggestion_data=video.ai_suggestion_data,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        error_message=video.error_message,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


# =============================================================================
# Schedule Single Video
# =============================================================================

@router.post("/schedule", response_model=ScheduleVideoResponse)
async def schedule_video(
    request: ScheduleVideoRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Schedule a single video for future generation and posting.
    
    Creates a planned video entry that will be:
    1. Generated 1 hour before scheduled_post_time
    2. Posted at scheduled_post_time to specified platforms
    """
    # Validate scheduled time is in the future (at least 2 hours from now)
    min_schedule_time = datetime.utcnow() + timedelta(hours=2)
    if request.scheduled_post_time < min_schedule_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be at least 2 hours in the future",
        )
    
    service = VideoPlanningService(db)
    
    try:
        video = await service.schedule_video(
            user_id=current_user.id,
            suggestion_data=request.suggestion_data.model_dump(),
            scheduled_post_time=request.scheduled_post_time,
            target_platforms=request.target_platforms,
            series_name=request.series_name,
            series_order=request.series_order,
        )
        
        return ScheduleVideoResponse(
            video=video_to_response(video),
            message="Video scheduled successfully",
        )
    except Exception as e:
        logger.exception(f"Failed to schedule video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule video: {str(e)}",
        )


# =============================================================================
# Create Series
# =============================================================================

@router.post("/series", response_model=CreateSeriesResponse)
async def create_video_series(
    request: CreateSeriesRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Create a video series with multiple scheduled parts.
    
    Creates multiple planned video entries with:
    - Shared series_name
    - Sequential series_order (1, 2, 3...)
    - Individual scheduled times from the schedule
    """
    # Validate all scheduled times
    min_time = datetime.utcnow() + timedelta(hours=2)
    for item in request.schedule:
        if item.scheduled_time < min_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All scheduled times must be at least 2 hours in the future. Video {item.video_index + 1} is too soon.",
            )
    
    service = VideoPlanningService(db)
    
    try:
        videos = await service.create_series(
            user_id=current_user.id,
            series_name=request.series_name,
            videos=[v.model_dump() for v in request.videos],
            schedule=[s.model_dump() for s in request.schedule],
            target_platforms=request.target_platforms,
        )
        
        return CreateSeriesResponse(
            series_name=request.series_name,
            videos=[video_to_response(v) for v in videos],
            total_videos=len(videos),
            message=f"Video series '{request.series_name}' created with {len(videos)} parts",
        )
    except Exception as e:
        logger.exception(f"Failed to create series: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create series: {str(e)}",
        )


# =============================================================================
# Create Monthly Plan
# =============================================================================

@router.post("/monthly-plan", response_model=CreateMonthlyPlanResponse)
async def create_monthly_plan(
    request: CreateMonthlyPlanRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Create a monthly content plan with multiple videos.
    """
    service = VideoPlanningService(db)
    
    try:
        videos = await service.create_monthly_plan(
            user_id=current_user.id,
            plan=request.plan.model_dump(),
        )
        
        return CreateMonthlyPlanResponse(
            month=request.plan.month,
            videos=[video_to_response(v) for v in videos],
            total_videos=len(videos),
            message=f"Monthly plan for {request.plan.month} created with {len(videos)} videos",
        )
    except Exception as e:
        logger.exception(f"Failed to create monthly plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create monthly plan: {str(e)}",
        )


# =============================================================================
# List Planned Videos
# =============================================================================

@router.get("/planned", response_model=PlannedVideoListResponse)
async def get_planned_videos(
    status_filter: Optional[str] = Query(default=None, description="Filter by planning_status"),
    series_name: Optional[str] = Query(default=None, description="Filter by series"),
    include_posted: bool = Query(default=False, description="Include posted videos"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Get all planned/scheduled videos for the user.
    
    By default excludes already posted videos.
    """
    query = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.planning_status != PlanningStatus.NONE.value,
    )
    
    if status_filter:
        query = query.filter(Video.planning_status == status_filter)
    
    if series_name:
        query = query.filter(Video.series_name == series_name)
    
    if not include_posted:
        query = query.filter(Video.planning_status != PlanningStatus.POSTED.value)
    
    query = query.order_by(Video.scheduled_post_time.asc())
    videos = query.all()
    
    # Group by series
    series_groups = {}
    for video in videos:
        if video.series_name:
            if video.series_name not in series_groups:
                series_groups[video.series_name] = []
            series_groups[video.series_name].append(video_to_response(video))
    
    return PlannedVideoListResponse(
        videos=[video_to_response(v) for v in videos],
        total=len(videos),
        series={k: v for k, v in series_groups.items()} if series_groups else None,
    )


# =============================================================================
# Update Planned Video
# =============================================================================

@router.patch("/planned/{video_id}", response_model=PlannedVideoResponse)
async def update_planned_video(
    video_id: UUID,
    request: UpdatePlannedVideoRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Update a planned video (reschedule, edit details, change platforms).
    
    Only videos with planning_status 'planned' can be fully edited.
    Videos in other states have limited edit capabilities.
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id,
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned video not found",
        )
    
    # Check if video can be edited
    if video.planning_status not in [
        PlanningStatus.PLANNED.value,
        PlanningStatus.READY.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit video in '{video.planning_status}' status",
        )
    
    # Apply updates
    if request.scheduled_post_time is not None:
        # Validate new time
        min_time = datetime.utcnow() + timedelta(hours=2)
        if request.scheduled_post_time < min_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be at least 2 hours in the future",
            )
        video.scheduled_post_time = request.scheduled_post_time
    
    if request.target_platforms is not None:
        video.target_platforms = request.target_platforms
    
    if request.title is not None:
        video.title = request.title
    
    if request.ai_suggestion_data is not None:
        video.ai_suggestion_data = request.ai_suggestion_data.model_dump()
    
    if request.series_name is not None:
        video.series_name = request.series_name
    
    if request.series_order is not None:
        video.series_order = request.series_order
    
    db.commit()
    db.refresh(video)
    
    return video_to_response(video)


# =============================================================================
# Delete Planned Video
# =============================================================================

@router.delete("/planned/{video_id}")
async def delete_planned_video(
    video_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Delete a planned video.
    
    Only videos with planning_status 'planned' or 'failed' can be deleted.
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id,
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned video not found",
        )
    
    # Check if video can be deleted
    if video.planning_status not in [
        PlanningStatus.PLANNED.value,
        PlanningStatus.FAILED.value,
        PlanningStatus.READY.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete video in '{video.planning_status}' status",
        )
    
    db.delete(video)
    db.commit()
    
    return {"message": "Planned video deleted successfully"}


# =============================================================================
# Trigger Generation
# =============================================================================

@router.post("/planned/{video_id}/generate-now", response_model=TriggerGenerationResponse)
async def trigger_generation_now(
    video_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Manually trigger generation for a planned video.
    
    Useful if user wants to generate immediately rather than waiting
    for the scheduled generation time.
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id,
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned video not found",
        )
    
    if video.planning_status != PlanningStatus.PLANNED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate video in '{video.planning_status}' status. Only 'planned' videos can be generated.",
        )
    
    service = VideoPlanningService(db)
    
    try:
        job_id = await service.trigger_generation(video)
        
        return TriggerGenerationResponse(
            message="Video generation started",
            job_id=job_id,
            video_id=video.id,
            estimated_time="5-15 minutes",
        )
    except Exception as e:
        logger.exception(f"Failed to trigger generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger generation: {str(e)}",
        )


# =============================================================================
# Calendar View
# =============================================================================

@router.get("/calendar", response_model=CalendarViewResponse)
async def get_calendar_view(
    start_date: datetime = Query(description="Start date for calendar range"),
    end_date: datetime = Query(description="End date for calendar range"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Get planned videos for calendar view.
    
    Returns videos scheduled within the given date range,
    with status indicators and quick action availability.
    """
    now = datetime.utcnow()
    
    videos = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.planning_status != PlanningStatus.NONE.value,
        Video.scheduled_post_time >= start_date,
        Video.scheduled_post_time <= end_date,
    ).order_by(Video.scheduled_post_time.asc()).all()
    
    items = []
    counts = {
        "planned": 0,
        "ready": 0,
        "posted": 0,
        "failed": 0,
    }
    
    for video in videos:
        is_overdue = (
            video.planning_status == PlanningStatus.PLANNED.value and
            video.scheduled_post_time and
            video.scheduled_post_time < now
        )
        
        can_generate = video.planning_status == PlanningStatus.PLANNED.value
        
        items.append(CalendarVideoItem(
            id=video.id,
            title=video.title or video.ai_suggestion_data.get("title") if video.ai_suggestion_data else None,
            planning_status=video.planning_status,
            scheduled_post_time=video.scheduled_post_time,
            target_platforms=video.target_platforms or [],
            series_name=video.series_name,
            series_order=video.series_order,
            thumbnail_url=video.thumbnail_url,
            is_overdue=is_overdue,
            can_generate_now=can_generate,
        ))
        
        # Update counts
        if video.planning_status in counts:
            counts[video.planning_status] += 1
    
    return CalendarViewResponse(
        items=items,
        start_date=start_date,
        end_date=end_date,
        total_planned=counts["planned"],
        total_ready=counts["ready"],
        total_posted=counts["posted"],
        total_failed=counts["failed"],
    )
