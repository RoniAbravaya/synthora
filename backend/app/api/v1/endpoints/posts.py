"""
Post API Endpoints

Handles video posting and scheduling to social media platforms.
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.services.post import PostService
from app.services.social_oauth import SocialOAuthService
from app.workers.scheduler import get_scheduler
from app.workers.post_worker import publish_post_now
from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.social_account import SocialPlatform
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    CalendarResponse,
    PublishNowRequest,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["Posts"])


# =============================================================================
# List Posts
# =============================================================================

@router.get("", response_model=PostListResponse)
async def list_posts(
    status_filter: Optional[PostStatus] = Query(default=None, alias="status"),
    platform: Optional[SocialPlatform] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all posts for the current user.
    
    **Query Parameters:**
    - `status`: Filter by post status
    - `platform`: Filter by platform
    - `skip`: Pagination offset
    - `limit`: Maximum records to return
    
    **Requires:** Authentication
    """
    post_service = PostService(db)
    
    posts, total = post_service.get_user_posts(
        user_id=user.id,
        status=status_filter,
        platform=platform,
        skip=skip,
        limit=limit,
    )
    
    return PostListResponse(
        posts=[_post_to_response(p) for p in posts],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/scheduled", response_model=List[PostResponse])
async def list_scheduled_posts(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List scheduled posts.
    
    **Query Parameters:**
    - `start_date`: Filter posts scheduled after this date
    - `end_date`: Filter posts scheduled before this date
    
    **Requires:** Authentication
    """
    post_service = PostService(db)
    
    posts = post_service.get_scheduled_posts(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
    )
    
    return [_post_to_response(p) for p in posts]


@router.get("/calendar/{year}/{month}", response_model=CalendarResponse)
async def get_calendar(
    year: int,
    month: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get calendar data for a month.
    
    **Path Parameters:**
    - `year`: Calendar year
    - `month`: Calendar month (1-12)
    
    **Requires:** Authentication
    """
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12",
        )
    
    post_service = PostService(db)
    calendar_data = post_service.get_calendar_data(user.id, year, month)
    
    return CalendarResponse(**calendar_data)


# =============================================================================
# Get Post
# =============================================================================

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a post by ID.
    
    **Path Parameters:**
    - `post_id`: UUID of the post
    
    **Requires:** Authentication (must own the post)
    """
    post_service = PostService(db)
    post = post_service.get_by_id(post_id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this post",
        )
    
    return _post_to_response(post)


# =============================================================================
# Create Post
# =============================================================================

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: PostCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new post.
    
    **Request Body:**
    - `video_id`: Video to post (required)
    - `platforms`: Target platforms (required)
    - `title`: Post title
    - `description`: Post description/caption
    - `hashtags`: Hashtags to include
    - `scheduled_at`: When to publish (None for draft)
    - `platform_overrides`: Platform-specific settings
    
    **Requires:** Authentication
    """
    post_service = PostService(db)
    oauth_service = SocialOAuthService(db)
    
    # Validate that user has accounts for all platforms
    for platform in request.platforms:
        accounts = oauth_service.get_user_accounts(user.id, platform)
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No {platform.value} account connected",
            )
    
    try:
        post = post_service.create_post(
            user_id=user.id,
            video_id=request.video_id,
            platforms=request.platforms,
            title=request.title,
            description=request.description,
            hashtags=request.hashtags,
            scheduled_at=request.scheduled_at,
            platform_overrides=request.platform_overrides,
        )
        
        # If scheduled, enqueue the job
        if post.scheduled_at and post.status == "scheduled":
            scheduler = get_scheduler()
            scheduler.enqueue_scheduled_post(post.id, post.scheduled_at)
        
        return _post_to_response(post)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Update Post
# =============================================================================

@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    request: PostUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a post.
    
    **Path Parameters:**
    - `post_id`: UUID of the post
    
    **Request Body:**
    - Any post fields to update
    
    **Requires:** Authentication (must own the post)
    """
    post_service = PostService(db)
    post = post_service.get_by_id(post_id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )
    
    try:
        post = post_service.update_post(
            post,
            title=request.title,
            description=request.description,
            hashtags=request.hashtags,
            platforms=request.platforms,
            scheduled_at=request.scheduled_at,
            platform_overrides=request.platform_overrides,
        )
        
        # If scheduled time changed, update the job
        if request.scheduled_at and post.status == PostStatus.SCHEDULED:
            scheduler = get_scheduler()
            scheduler.enqueue_scheduled_post(post.id, post.scheduled_at)
        
        return _post_to_response(post)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Delete Post
# =============================================================================

@router.delete("/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a post.
    
    **Path Parameters:**
    - `post_id`: UUID of the post
    
    **Requires:** Authentication (must own the post)
    """
    post_service = PostService(db)
    post = post_service.get_by_id(post_id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )
    
    try:
        post_service.delete_post(post)
        return MessageResponse(message="Post deleted")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Publish Post
# =============================================================================

@router.post("/{post_id}/publish", response_model=PostResponse)
async def publish_post(
    post_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Publish a post immediately.
    
    **Path Parameters:**
    - `post_id`: UUID of the post
    
    **Requires:** Authentication (must own the post)
    """
    post_service = PostService(db)
    post = post_service.get_by_id(post_id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to publish this post",
        )
    
    if post.status not in ["draft", "scheduled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish post in status: {post.status.value}",
        )
    
    # Enqueue immediate publish job
    scheduler = get_scheduler()
    job = scheduler.queues["posts"].enqueue(
        publish_post_now,
        post_id=str(post.id),
        job_timeout="5m",
    )
    
    # Update post status
    post_service.start_publishing(post)
    
    return _post_to_response(post)


# =============================================================================
# Stats
# =============================================================================

@router.get("/stats/me", response_model=dict)
async def get_my_post_stats(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get post statistics for the current user.
    
    **Requires:** Authentication
    """
    post_service = PostService(db)
    return post_service.get_user_post_stats(user.id)


# =============================================================================
# Helper Functions
# =============================================================================

def _post_to_response(post: Post) -> PostResponse:
    """Convert a Post model to PostResponse."""
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        video_id=post.video_id,
        title=post.title,
        description=post.description,
        hashtags=post.hashtags or [],
        platforms=post.platforms or [],
        platform_status=post.platform_status or {},
        platform_overrides=post.platform_overrides or {},
        status=post.status,
        scheduled_at=post.scheduled_at,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )
