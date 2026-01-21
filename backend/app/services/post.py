"""
Post Service

Business logic for managing video posts and scheduling.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from calendar import monthrange

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.post import Post, PostStatus, PostPlatformStatus
from app.models.video import Video, VideoStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.user import User

logger = logging.getLogger(__name__)


class PostService:
    """
    Service class for post management operations.
    
    Handles:
    - CRUD operations for posts
    - Cross-posting to multiple platforms
    - Scheduling and calendar views
    - Post status tracking
    """
    
    def __init__(self, db: Session):
        """
        Initialize the post service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_by_id(self, post_id: UUID) -> Optional[Post]:
        """Get a post by ID."""
        return self.db.query(Post).filter(Post.id == post_id).first()
    
    def get_user_posts(
        self,
        user_id: UUID,
        status: Optional[PostStatus] = None,
        platform: Optional[SocialPlatform] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Post], int]:
        """
        Get all posts for a user.
        
        Args:
            user_id: User's UUID
            status: Filter by status
            platform: Filter by platform
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (posts list, total count)
        """
        query = self.db.query(Post).filter(Post.user_id == user_id)
        
        if status:
            query = query.filter(Post.status == status)
        
        if platform:
            query = query.filter(Post.platforms.contains([platform.value]))
        
        total = query.count()
        
        posts = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        return posts, total
    
    def get_scheduled_posts(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Post]:
        """
        Get scheduled posts for a user.
        
        Args:
            user_id: User's UUID
            start_date: Filter posts scheduled after this date
            end_date: Filter posts scheduled before this date
            
        Returns:
            List of scheduled posts
        """
        query = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == PostStatus.SCHEDULED,
            )
        )
        
        if start_date:
            query = query.filter(Post.scheduled_at >= start_date)
        
        if end_date:
            query = query.filter(Post.scheduled_at <= end_date)
        
        return query.order_by(Post.scheduled_at.asc()).all()
    
    def get_pending_scheduled_posts(self, limit: int = 100) -> List[Post]:
        """
        Get posts that are due for publishing.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of posts ready to publish
        """
        now = datetime.utcnow()
        
        return self.db.query(Post).filter(
            and_(
                Post.status == PostStatus.SCHEDULED,
                Post.scheduled_at <= now,
            )
        ).order_by(Post.scheduled_at.asc()).limit(limit).all()
    
    def get_calendar_data(
        self,
        user_id: UUID,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """
        Get calendar data for a month.
        
        Args:
            user_id: User's UUID
            year: Calendar year
            month: Calendar month (1-12)
            
        Returns:
            Dictionary with calendar data
        """
        # Get first and last day of month
        _, last_day = monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        # Get all posts for the month
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                or_(
                    and_(
                        Post.scheduled_at >= start_date,
                        Post.scheduled_at <= end_date,
                    ),
                    and_(
                        Post.published_at >= start_date,
                        Post.published_at <= end_date,
                    ),
                ),
            )
        ).all()
        
        # Group by day
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        
        for post in posts:
            post_date = post.scheduled_at or post.published_at
            if post_date:
                day = post_date.day
                if day not in by_day:
                    by_day[day] = []
                
                by_day[day].append({
                    "id": str(post.id),
                    "video_id": str(post.video_id),
                    "title": post.title,
                    "status": post.status.value,
                    "platforms": post.platforms,
                    "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                })
        
        return {
            "year": year,
            "month": month,
            "days": by_day,
            "total_posts": len(posts),
        }
    
    # =========================================================================
    # Create/Update Methods
    # =========================================================================
    
    def create_post(
        self,
        user_id: UUID,
        video_id: UUID,
        platforms: List[SocialPlatform],
        title: Optional[str] = None,
        description: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
        platform_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Post:
        """
        Create a new post.
        
        Args:
            user_id: User's UUID
            video_id: Video to post
            platforms: Target platforms
            title: Post title
            description: Post description/caption
            hashtags: Hashtags to include
            scheduled_at: When to publish (None for draft)
            platform_overrides: Platform-specific overrides
            
        Returns:
            Newly created Post instance
        """
        # Validate video
        video = self.db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError("Video not found")
        
        if video.user_id != user_id:
            raise ValueError("Not authorized to post this video")
        
        if video.status != VideoStatus.COMPLETED:
            raise ValueError("Video must be completed before posting")
        
        # Determine initial status
        if scheduled_at:
            status = PostStatus.SCHEDULED
        else:
            status = PostStatus.DRAFT
        
        # Initialize platform statuses
        platform_status = {
            p.value: {"status": "pending", "post_id": None, "post_url": None}
            for p in platforms
        }
        
        post = Post(
            user_id=user_id,
            video_id=video_id,
            title=title or video.title,
            description=description,
            hashtags=hashtags or [],
            platforms=[p.value for p in platforms],
            platform_status=platform_status,
            platform_overrides=platform_overrides or {},
            status=status,
            scheduled_at=scheduled_at,
        )
        
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        
        logger.info(f"Created post: {post.id} for video {video_id}")
        return post
    
    def update_post(
        self,
        post: Post,
        title: Optional[str] = None,
        description: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        platforms: Optional[List[SocialPlatform]] = None,
        scheduled_at: Optional[datetime] = None,
        platform_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Post:
        """
        Update a post.
        
        Args:
            post: Post to update
            title: New title
            description: New description
            hashtags: New hashtags
            platforms: New platforms
            scheduled_at: New scheduled time
            platform_overrides: New platform overrides
            
        Returns:
            Updated Post instance
        """
        if post.status in [PostStatus.PUBLISHING, PostStatus.PUBLISHED]:
            raise ValueError("Cannot update a post that is publishing or published")
        
        if title is not None:
            post.title = title
        
        if description is not None:
            post.description = description
        
        if hashtags is not None:
            post.hashtags = hashtags
        
        if platforms is not None:
            post.platforms = [p.value for p in platforms]
            # Update platform status
            current_statuses = post.platform_status or {}
            new_statuses = {}
            for p in platforms:
                if p.value in current_statuses:
                    new_statuses[p.value] = current_statuses[p.value]
                else:
                    new_statuses[p.value] = {"status": "pending", "post_id": None, "post_url": None}
            post.platform_status = new_statuses
        
        if scheduled_at is not None:
            post.scheduled_at = scheduled_at
            if scheduled_at and post.status == PostStatus.DRAFT:
                post.status = PostStatus.SCHEDULED
        
        if platform_overrides is not None:
            post.platform_overrides = platform_overrides
        
        self.db.commit()
        self.db.refresh(post)
        
        logger.info(f"Updated post: {post.id}")
        return post
    
    def delete_post(self, post: Post) -> None:
        """
        Delete a post.
        
        Args:
            post: Post to delete
        """
        if post.status == PostStatus.PUBLISHING:
            raise ValueError("Cannot delete a post that is currently publishing")
        
        post_id = post.id
        
        self.db.delete(post)
        self.db.commit()
        
        logger.info(f"Deleted post: {post_id}")
    
    # =========================================================================
    # Publishing Methods
    # =========================================================================
    
    def start_publishing(self, post: Post) -> Post:
        """
        Mark a post as starting to publish.
        
        Args:
            post: Post to publish
            
        Returns:
            Updated Post instance
        """
        if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED, PostStatus.PARTIALLY_PUBLISHED]:
            raise ValueError(f"Cannot publish post in status: {post.status.value}")
        
        post.status = PostStatus.PUBLISHING
        
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def update_platform_status(
        self,
        post: Post,
        platform: SocialPlatform,
        status: str,
        post_id: Optional[str] = None,
        post_url: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Post:
        """
        Update the status for a specific platform.
        
        Args:
            post: Post to update
            platform: Platform to update
            status: New status (pending, publishing, published, failed)
            post_id: Platform-specific post ID
            post_url: URL to the post
            error: Error message if failed
            
        Returns:
            Updated Post instance
        """
        if post.platform_status is None:
            post.platform_status = {}
        
        post.platform_status[platform.value] = {
            "status": status,
            "post_id": post_id,
            "post_url": post_url,
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Update overall status based on platform statuses
        self._update_overall_status(post)
        
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def _update_overall_status(self, post: Post) -> None:
        """Update overall post status based on platform statuses."""
        if not post.platform_status:
            return
        
        statuses = [s.get("status") for s in post.platform_status.values()]
        
        if all(s == "published" for s in statuses):
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.utcnow()
        elif all(s == "failed" for s in statuses):
            post.status = PostStatus.FAILED
        elif any(s == "published" for s in statuses) and any(s == "failed" for s in statuses):
            post.status = PostStatus.PARTIALLY_PUBLISHED
        elif any(s == "publishing" for s in statuses):
            post.status = PostStatus.PUBLISHING
    
    def complete_publishing(
        self,
        post: Post,
        results: Dict[str, Dict[str, Any]],
    ) -> Post:
        """
        Complete publishing with results from all platforms.
        
        Args:
            post: Post to complete
            results: Results by platform
            
        Returns:
            Updated Post instance
        """
        for platform_str, result in results.items():
            platform = SocialPlatform(platform_str)
            
            if result.get("success"):
                self.update_platform_status(
                    post,
                    platform,
                    "published",
                    post_id=result.get("post_id"),
                    post_url=result.get("post_url"),
                )
            else:
                self.update_platform_status(
                    post,
                    platform,
                    "failed",
                    error=result.get("error"),
                )
        
        return post
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_user_post_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get post statistics for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with post statistics
        """
        total = self.db.query(Post).filter(Post.user_id == user_id).count()
        
        by_status = {}
        for status in PostStatus:
            count = self.db.query(Post).filter(
                and_(Post.user_id == user_id, Post.status == status)
            ).count()
            by_status[status.value] = count
        
        # Scheduled this week
        week_start = datetime.utcnow()
        week_end = week_start + timedelta(days=7)
        scheduled_this_week = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == PostStatus.SCHEDULED,
                Post.scheduled_at >= week_start,
                Post.scheduled_at <= week_end,
            )
        ).count()
        
        return {
            "total": total,
            "by_status": by_status,
            "scheduled_this_week": scheduled_this_week,
        }


def get_post_service(db: Session) -> PostService:
    """Factory function to create a PostService instance."""
    return PostService(db)

