"""
API Logs Admin Endpoints

Admin endpoints for viewing and analyzing API request logs.
Used for debugging and monitoring external API integrations.
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.auth import require_admin
from app.models.user import User
from app.models.api_request_log import APIRequestLog
from app.schemas.api_logs import (
    APILogResponse,
    APILogDetailResponse,
    APILogsListResponse,
    ProviderStatsResponse,
    AllProviderStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api-logs", tags=["Admin - API Logs"])


@router.get("", response_model=APILogsListResponse)
async def list_api_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    video_id: Optional[UUID] = Query(None, description="Filter by video ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    generation_step: Optional[str] = Query(None, description="Filter by generation step"),
    is_error: Optional[bool] = Query(None, description="Filter errors only"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List API request logs with filtering.
    
    **Query Parameters:**
    - `user_id`: Filter by user
    - `video_id`: Filter by video
    - `provider`: Filter by provider (e.g., "openai_gpt", "elevenlabs")
    - `generation_step`: Filter by step (e.g., "script", "voice")
    - `is_error`: Filter for errors only (status_code >= 400 or error_message)
    - `start_date`: Filter from date
    - `end_date`: Filter to date
    - `limit`: Maximum records to return (default 100)
    - `offset`: Pagination offset
    
    **Requires:** Admin role
    """
    query = db.query(APIRequestLog)
    
    if user_id:
        query = query.filter(APIRequestLog.user_id == user_id)
    
    if video_id:
        query = query.filter(APIRequestLog.video_id == video_id)
    
    if provider:
        query = query.filter(APIRequestLog.provider == provider)
    
    if generation_step:
        query = query.filter(APIRequestLog.generation_step == generation_step)
    
    if is_error is True:
        query = query.filter(
            (APIRequestLog.status_code >= 400) |
            (APIRequestLog.error_message != None)
        )
    elif is_error is False:
        query = query.filter(
            (APIRequestLog.status_code < 400) |
            (APIRequestLog.status_code == None)
        ).filter(APIRequestLog.error_message == None)
    
    if start_date:
        query = query.filter(APIRequestLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(APIRequestLog.created_at <= end_date)
    
    total = query.count()
    logs = query.order_by(desc(APIRequestLog.created_at)).offset(offset).limit(limit).all()
    
    return APILogsListResponse(
        logs=[_log_to_response(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=AllProviderStatsResponse)
async def get_provider_stats(
    period_hours: int = Query(24, ge=1, le=720, description="Period in hours"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get statistics for all providers over a time period.
    
    **Query Parameters:**
    - `period_hours`: Time period in hours (default 24, max 720 = 30 days)
    
    **Requires:** Admin role
    """
    cutoff = datetime.utcnow() - timedelta(hours=period_hours)
    
    # Query stats grouped by provider
    stats_query = db.query(
        APIRequestLog.provider,
        func.count(APIRequestLog.id).label("total_requests"),
        func.sum(
            func.cast(
                (APIRequestLog.status_code < 400) &
                (APIRequestLog.error_message == None),
                db.bind.dialect.name == "postgresql" and "INTEGER" or "INTEGER"
            )
        ).label("success_count"),
        func.avg(APIRequestLog.duration_ms).label("avg_duration"),
    ).filter(
        APIRequestLog.created_at >= cutoff
    ).group_by(
        APIRequestLog.provider
    ).all()
    
    # Build response
    stats = []
    for row in stats_query:
        total = row.total_requests or 0
        success = row.success_count or 0
        error_count = total - success
        error_rate = (error_count / total * 100) if total > 0 else 0.0
        
        stats.append(ProviderStatsResponse(
            provider=row.provider,
            period_hours=period_hours,
            total_requests=total,
            success_count=success,
            error_count=error_count,
            avg_duration_ms=int(row.avg_duration or 0),
            error_rate=round(error_rate, 2),
        ))
    
    return AllProviderStatsResponse(
        stats=sorted(stats, key=lambda x: x.total_requests, reverse=True),
        period_hours=period_hours,
    )


@router.get("/{log_id}", response_model=APILogDetailResponse)
async def get_api_log_detail(
    log_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a specific API log.
    
    Includes full request/response bodies (masked for sensitive data).
    
    **Path Parameters:**
    - `log_id`: UUID of the log entry
    
    **Requires:** Admin role
    """
    log = db.query(APIRequestLog).filter(APIRequestLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API log not found",
        )
    
    return _log_to_detail_response(log)


@router.get("/video/{video_id}", response_model=List[APILogDetailResponse])
async def get_video_api_logs(
    video_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get all API logs for a specific video.
    
    Useful for debugging a video generation.
    
    **Path Parameters:**
    - `video_id`: UUID of the video
    
    **Requires:** Admin role
    """
    logs = db.query(APIRequestLog).filter(
        APIRequestLog.video_id == video_id
    ).order_by(
        APIRequestLog.created_at.asc()
    ).all()
    
    return [_log_to_detail_response(log) for log in logs]


@router.delete("/cleanup")
async def cleanup_old_logs(
    older_than_days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete old API logs.
    
    **Query Parameters:**
    - `older_than_days`: Delete logs older than this many days (default 30)
    
    **Requires:** Admin role
    """
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    
    deleted_count = db.query(APIRequestLog).filter(
        APIRequestLog.created_at < cutoff
    ).delete()
    
    db.commit()
    
    logger.info(f"Deleted {deleted_count} API logs older than {older_than_days} days")
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff.isoformat(),
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _log_to_response(log: APIRequestLog) -> APILogResponse:
    """Convert a log model to basic response."""
    is_error = (
        (log.status_code and log.status_code >= 400) or
        log.error_message is not None
    )
    
    return APILogResponse(
        id=str(log.id),
        user_id=str(log.user_id) if log.user_id else None,
        video_id=str(log.video_id) if log.video_id else None,
        provider=log.provider,
        endpoint=log.endpoint,
        method=log.method,
        status_code=log.status_code,
        duration_ms=log.duration_ms,
        is_success=not is_error,
        is_error=is_error,
        error_message=log.error_message,
        generation_step=log.generation_step,
        created_at=str(log.created_at),
    )


def _log_to_detail_response(log: APIRequestLog) -> APILogDetailResponse:
    """Convert a log model to detailed response."""
    is_error = (
        (log.status_code and log.status_code >= 400) or
        log.error_message is not None
    )
    
    return APILogDetailResponse(
        id=str(log.id),
        user_id=str(log.user_id) if log.user_id else None,
        video_id=str(log.video_id) if log.video_id else None,
        provider=log.provider,
        endpoint=log.endpoint,
        method=log.method,
        status_code=log.status_code,
        duration_ms=log.duration_ms,
        is_success=not is_error,
        is_error=is_error,
        error_message=log.error_message,
        generation_step=log.generation_step,
        created_at=str(log.created_at),
        request_body=log.request_body,
        response_body=log.response_body,
        error_details=log.error_details,
    )
