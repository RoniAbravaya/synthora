"""
Video Service

Business logic for managing video records and generation jobs.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.video import Video, VideoStatus, GenerationStep
from app.models.user import User, UserRole
from app.models.job import Job, JobType, JobStatus

logger = logging.getLogger(__name__)


class VideoService:
    """
    Service class for video management operations.
    
    Handles:
    - CRUD operations for videos
    - Video status tracking
    - Generation state management
    - Expiration handling
    """
    
    def __init__(self, db: Session):
        """
        Initialize the video service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_by_id(self, video_id: UUID) -> Optional[Video]:
        """Get a video by ID."""
        return self.db.query(Video).filter(Video.id == video_id).first()
    
    def get_user_videos(
        self,
        user_id: UUID,
        status: Optional[VideoStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Video], int]:
        """
        Get all videos for a user.
        
        Args:
            user_id: User's UUID
            status: Filter by status
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (videos list, total count)
        """
        query = self.db.query(Video).filter(Video.user_id == user_id)
        
        if status:
            query = query.filter(Video.status == status)
        
        # Exclude expired videos
        query = query.filter(
            or_(
                Video.expires_at.is_(None),
                Video.expires_at > datetime.utcnow(),
            )
        )
        
        total = query.count()
        
        videos = query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
        
        return videos, total
    
    def get_active_generation(self, user_id: UUID) -> Optional[Video]:
        """
        Get the currently generating video for a user.
        
        Used to enforce concurrent generation limits.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Video instance if one is generating, None otherwise
        """
        return self.db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.status.in_(["pending", "processing"]),
            )
        ).first()
    
    def count_videos_today(self, user_id: UUID) -> int:
        """
        Count videos created by user today.
        
        Used for daily limit enforcement.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of videos created today
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return self.db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.created_at >= today_start,
            )
        ).count()
    
    # =========================================================================
    # Create/Update Methods
    # =========================================================================
    
    def create_video(
        self,
        user_id: UUID,
        prompt: str,
        template_id: Optional[UUID] = None,
        title: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Video:
        """
        Create a new video record.
        
        Args:
            user_id: User's UUID
            prompt: Main topic/prompt for the video
            template_id: Template to use (optional)
            title: Video title (optional)
            expires_at: Expiration date (optional)
            
        Returns:
            Newly created Video instance
        """
        video = Video(
            user_id=user_id,
            template_id=template_id,
            title=title,
            prompt=prompt,
            status="pending",
            progress=0,
            expires_at=expires_at,
        )
        
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        
        logger.info(f"Created video: {video.id} for user {user_id}")
        return video
    
    def create_generation_job(self, video: Video) -> Job:
        """
        Create a background job for video generation.
        
        Args:
            video: Video to generate
            
        Returns:
            Job instance
        """
        job = Job(
            user_id=video.user_id,
            type=JobType.VIDEO_GENERATION,
            status=JobStatus.PENDING,
            payload={
                "video_id": str(video.id),
                "prompt": video.prompt,
                "template_id": str(video.template_id) if video.template_id else None,
            },
            progress=0,
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created generation job: {job.id} for video {video.id}")
        return job
    
    def update_status(
        self,
        video: Video,
        status: VideoStatus,
        current_step: Optional[GenerationStep] = None,
        progress: Optional[int] = None,
    ) -> Video:
        """
        Update video generation status.
        
        Args:
            video: Video to update
            status: New status
            current_step: Current generation step
            progress: Overall progress percentage
            
        Returns:
            Updated Video instance
        """
        video.status = status
        
        if current_step is not None:
            video.current_step = current_step
        
        if progress is not None:
            video.progress = progress
        
        self.db.commit()
        self.db.refresh(video)
        
        logger.info(f"Video {video.id} status updated to {status.value}")
        return video
    
    def update_step(
        self,
        video: Video,
        step: GenerationStep,
        step_status: str,
        progress: int = 0,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Video:
        """
        Update a specific generation step.
        
        Args:
            video: Video to update
            step: Generation step to update
            step_status: Status of the step (pending, processing, completed, failed)
            progress: Step progress percentage
            result: Step result data
            error: Error message if failed
            
        Returns:
            Updated Video instance
        """
        video.update_step(step, step_status, progress, result, error)
        
        self.db.commit()
        self.db.refresh(video)
        
        return video
    
    def complete_video(
        self,
        video: Video,
        video_url: str,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        file_size: Optional[int] = None,
        resolution: Optional[str] = None,
        integrations_used: Optional[List[str]] = None,
        generation_time: Optional[float] = None,
    ) -> Video:
        """
        Mark a video as completed.
        
        Args:
            video: Video to complete
            video_url: URL to the generated video
            thumbnail_url: URL to thumbnail
            duration: Video duration in seconds
            file_size: File size in bytes
            resolution: Video resolution (e.g., "1080x1920")
            integrations_used: List of integrations used
            generation_time: Total generation time in seconds
            
        Returns:
            Updated Video instance
        """
        video.status = "completed"
        video.progress = 100
        video.video_url = video_url
        video.thumbnail_url = thumbnail_url
        video.duration = duration
        video.file_size = file_size
        video.resolution = resolution
        video.integrations_used = integrations_used or []
        video.generation_time_seconds = generation_time
        
        self.db.commit()
        self.db.refresh(video)
        
        logger.info(f"Video {video.id} completed successfully")
        return video
    
    def fail_video(
        self,
        video: Video,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Video:
        """
        Mark a video as failed.
        
        Args:
            video: Video to fail
            error_message: Error message
            error_details: Full error details (payload, stack trace, etc.)
            
        Returns:
            Updated Video instance
        """
        video.set_error(error_message, error_details)
        
        self.db.commit()
        self.db.refresh(video)
        
        logger.error(f"Video {video.id} failed: {error_message}")
        return video
    
    def delete_video(self, video: Video) -> None:
        """
        Delete a video.
        
        Args:
            video: Video to delete
        """
        video_id = video.id
        
        self.db.delete(video)
        self.db.commit()
        
        logger.info(f"Deleted video: {video_id}")
    
    # =========================================================================
    # Generation State Management
    # =========================================================================
    
    def get_last_successful_step(self, video: Video) -> Optional[GenerationStep]:
        """
        Get the last successfully completed step.
        
        Useful for resuming failed generations.
        
        Args:
            video: Video to check
            
        Returns:
            Last successful GenerationStep, or None
        """
        return video.get_last_successful_step()
    
    def can_swap_integration(self, video: Video, step: GenerationStep) -> bool:
        """
        Check if an integration can be swapped for a step.
        
        Args:
            video: Video to check
            step: Step to swap integration for
            
        Returns:
            True if swap is possible
        """
        # Can only swap if the step failed
        step_data = video.get_step_status(step)
        return step_data.get("status") == "failed"
    
    # =========================================================================
    # Expiration Management
    # =========================================================================
    
    def set_expiration(
        self,
        video: Video,
        retention_days: int,
    ) -> Video:
        """
        Set video expiration date.
        
        Args:
            video: Video to update
            retention_days: Number of days to retain
            
        Returns:
            Updated Video instance
        """
        video.expires_at = datetime.utcnow() + timedelta(days=retention_days)
        
        self.db.commit()
        self.db.refresh(video)
        
        return video
    
    def get_expired_videos(self, limit: int = 100) -> List[Video]:
        """
        Get videos that have expired.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of expired Video instances
        """
        return self.db.query(Video).filter(
            and_(
                Video.expires_at.isnot(None),
                Video.expires_at <= datetime.utcnow(),
            )
        ).limit(limit).all()
    
    def cleanup_expired_videos(self) -> int:
        """
        Delete expired videos.
        
        Returns:
            Number of videos deleted
        """
        expired = self.get_expired_videos()
        count = len(expired)
        
        for video in expired:
            self.db.delete(video)
        
        if count > 0:
            self.db.commit()
            logger.info(f"Cleaned up {count} expired videos")
        
        return count
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_user_video_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get video statistics for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with video statistics
        """
        total = self.db.query(Video).filter(Video.user_id == user_id).count()
        
        by_status = {}
        for status in VideoStatus:
            count = self.db.query(Video).filter(
                and_(Video.user_id == user_id, Video.status == status)
            ).count()
            by_status[status.value] = count
        
        today_count = self.count_videos_today(user_id)
        
        return {
            "total": total,
            "by_status": by_status,
            "today": today_count,
        }
    
    def get_platform_video_stats(self) -> Dict[str, Any]:
        """
        Get platform-wide video statistics.
        
        Returns:
            Dictionary with platform video statistics
        """
        total = self.db.query(Video).count()
        
        by_status = {}
        for status in VideoStatus:
            count = self.db.query(Video).filter(Video.status == status).count()
            by_status[status.value] = count
        
        # Videos this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = self.db.query(Video).filter(
            Video.created_at >= month_start
        ).count()
        
        return {
            "total": total,
            "by_status": by_status,
            "this_month": this_month,
        }


def get_video_service(db: Session) -> VideoService:
    """Factory function to create a VideoService instance."""
    return VideoService(db)

