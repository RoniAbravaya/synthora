"""
Analytics API Endpoints

Endpoints for fetching and syncing analytics data.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_premium
from app.models.user import User
from app.models.social_account import SocialPlatform
from app.services.analytics import AnalyticsService
from app.workers.analytics_worker import (
    queue_analytics_sync,
    queue_user_analytics_sync,
    sync_channel_analytics_job,
)
from app.schemas.analytics import (
    OverviewResponse,
    SummaryMetrics,
    PlatformComparisonResponse,
    PlatformMetrics,
    TopPerformingResponse,
    TopPerformingItem,
    PostMetrics,
    TimeSeriesResponse,
    TimeSeriesDataPoint,
    HeatmapResponse,
    HeatmapHourData,
    SyncResponse,
    PostAnalyticsResponse,
    AnalyticsMetrics,
    ChannelAnalyticsResponse,
    ChannelMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# =============================================================================
# Overview Endpoints
# =============================================================================

@router.get("/overview", response_model=OverviewResponse)
async def get_analytics_overview(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get analytics overview for the current user.
    
    Returns aggregated metrics across all platforms for the specified period.
    """
    service = AnalyticsService(db)
    data = service.get_user_analytics_overview(current_user.id, days)
    
    return OverviewResponse(
        period_days=data["period_days"],
        total_posts=data["total_posts"],
        summary=SummaryMetrics(**data["summary"]),
        by_platform=data["by_platform"],
    )


@router.get("/platforms", response_model=PlatformComparisonResponse)
async def get_platform_comparison(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get platform comparison data.
    
    Compares performance across different social media platforms.
    """
    service = AnalyticsService(db)
    data = service.get_platform_comparison(current_user.id, days)
    
    platforms = [
        PlatformMetrics(**p) for p in data["platforms"]
    ]
    
    return PlatformComparisonResponse(
        period_days=data["period_days"],
        platforms=platforms,
    )


# =============================================================================
# Time Series Endpoints
# =============================================================================

@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    metric: str = Query(
        default="views",
        description="Metric to retrieve (views, likes, comments, shares)"
    ),
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get time series data for a specific metric.
    
    Returns daily data points for charting.
    """
    # Validate metric
    valid_metrics = ["views", "likes", "comments", "shares"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {valid_metrics}",
        )
    
    # Validate platform if provided
    analytics_platform = None
    if platform:
        try:
            analytics_platform = SocialPlatform(platform.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform: {platform}",
            )
    
    service = AnalyticsService(db)
    data_points = service.get_time_series(
        current_user.id,
        metric,
        days,
        analytics_platform,
    )
    
    return TimeSeriesResponse(
        metric=metric,
        days=days,
        platform=platform,
        data_points=[TimeSeriesDataPoint(**dp) for dp in data_points],
    )


# =============================================================================
# Top Performers Endpoints
# =============================================================================

@router.get("/top-performing", response_model=TopPerformingResponse)
async def get_top_performing(
    metric: str = Query(default="views", description="Metric to sort by"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of results"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get top performing posts by a specific metric.
    """
    # Validate metric
    valid_metrics = ["views", "likes", "comments", "shares"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {valid_metrics}",
        )
    
    # Validate platform if provided
    analytics_platform = None
    if platform:
        try:
            analytics_platform = SocialPlatform(platform.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform: {platform}",
            )
    
    service = AnalyticsService(db)
    items = service.get_top_performing(
        current_user.id,
        metric,
        limit,
        analytics_platform,
    )
    
    return TopPerformingResponse(
        metric=metric,
        limit=limit,
        items=[
            TopPerformingItem(
                post_id=item["post_id"],
                video_id=item["video_id"],
                title=item["title"],
                thumbnail_url=item.get("thumbnail_url"),
                platforms=item.get("platforms", []),
                published_at=item.get("published_at"),
                metrics=PostMetrics(**item["metrics"]),
            )
            for item in items
        ],
    )


# =============================================================================
# Heatmap Endpoints
# =============================================================================

@router.get("/heatmap", response_model=HeatmapResponse)
async def get_posting_heatmap(
    days: int = Query(default=90, ge=30, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get posting time heatmap data.
    
    Shows engagement patterns by day of week and hour to help
    determine optimal posting times.
    """
    service = AnalyticsService(db)
    data = service.get_posting_heatmap(current_user.id, days)
    
    # Convert heatmap to response format
    heatmap_response = {}
    for day_name, hours in data["heatmap"].items():
        heatmap_response[day_name] = {
            hour: HeatmapHourData(**hour_data)
            for hour, hour_data in hours.items()
        }
    
    # Find best times (top 5 by engagement)
    best_times = []
    for day_name, hours in data["heatmap"].items():
        for hour, hour_data in hours.items():
            if hour_data["posts"] > 0:
                best_times.append({
                    "day": day_name,
                    "hour": int(hour),
                    "avg_engagement": hour_data["avg_engagement"],
                    "posts": hour_data["posts"],
                })
    
    best_times.sort(key=lambda x: x["avg_engagement"], reverse=True)
    best_times = best_times[:5]
    
    return HeatmapResponse(
        period_days=data["period_days"],
        heatmap=heatmap_response,
        best_times=best_times,
    )


# =============================================================================
# Post Analytics Endpoints
# =============================================================================

@router.get("/posts/{post_id}", response_model=PostAnalyticsResponse)
async def get_post_analytics(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed analytics for a specific post.
    """
    from app.models.post import Post
    
    # Verify post ownership
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == current_user.id,
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    service = AnalyticsService(db)
    analytics_list = service.get_post_analytics(post_id)
    
    # Group by platform
    platforms = {}
    total = {
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "saves": 0,
        "engagement_rate": 0.0,
    }
    
    last_synced = None
    
    for analytics in analytics_list:
        platform_name = analytics.platform.value
        
        if platform_name not in platforms:
            platforms[platform_name] = AnalyticsMetrics(
                views=analytics.views,
                likes=analytics.likes,
                comments=analytics.comments,
                shares=analytics.shares,
                saves=analytics.saves,
                engagement_rate=analytics.engagement_rate,
                watch_time_seconds=analytics.watch_time_seconds,
                avg_view_duration=analytics.avg_view_duration,
                reach=analytics.reach,
                impressions=analytics.impressions,
            )
        
        # Add to totals
        total["views"] += analytics.views
        total["likes"] += analytics.likes
        total["comments"] += analytics.comments
        total["shares"] += analytics.shares
        total["saves"] += analytics.saves
        
        # Track last synced
        if not last_synced or analytics.fetched_at > last_synced:
            last_synced = analytics.fetched_at
    
    # Calculate total engagement rate
    if total["views"] > 0:
        total["engagement_rate"] = round(
            ((total["likes"] + total["comments"] + total["shares"]) / total["views"]) * 100,
            2
        )
    
    return PostAnalyticsResponse(
        post_id=str(post_id),
        platforms=platforms,
        total=AnalyticsMetrics(**total),
        last_synced=last_synced,
    )


# =============================================================================
# Sync Endpoints
# =============================================================================

@router.post("/sync", response_model=SyncResponse)
async def sync_all_analytics(
    current_user: User = Depends(get_current_active_user),
):
    """
    Trigger analytics sync for all user's posts.
    
    Queues a background job to fetch latest analytics from all platforms.
    """
    job_id = queue_user_analytics_sync(current_user.id)
    
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue analytics sync",
        )
    
    return SyncResponse(
        message="Analytics sync queued successfully",
        job_id=job_id,
        estimated_time="2-5 minutes depending on number of posts",
    )


@router.post("/sync/{post_id}", response_model=SyncResponse)
async def sync_post_analytics(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Trigger analytics sync for a specific post.
    """
    from app.models.post import Post, PostStatus
    
    # Verify post ownership and status
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == current_user.id,
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status != PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only sync analytics for published posts",
        )
    
    job_id = queue_analytics_sync(post_id)
    
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue analytics sync",
        )
    
    return SyncResponse(
        message="Post analytics sync queued successfully",
        job_id=job_id,
        estimated_time="30-60 seconds",
    )


# =============================================================================
# Channel Analytics Endpoints (Premium)
# =============================================================================

@router.get("/channels", response_model=ChannelAnalyticsResponse)
async def get_channel_analytics(
    current_user: User = Depends(require_premium),
):
    """
    Get channel/account-level analytics for all connected platforms.
    
    Premium feature only.
    """
    result = sync_channel_analytics_job(str(current_user.id))
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to fetch channel analytics"),
        )
    
    channels = [
        ChannelMetrics(platform=platform, data=data)
        for platform, data in result.get("channels", {}).items()
    ]
    
    return ChannelAnalyticsResponse(channels=channels)
