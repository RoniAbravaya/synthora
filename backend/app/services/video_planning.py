"""
Video Planning Service

Business logic for scheduling videos and creating content plans.
Handles single video scheduling, series creation, and monthly plans.
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.video import Video, PlanningStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class VideoPlanningService:
    """
    Service for video planning and scheduling operations.
    
    Handles:
    - Scheduling single videos
    - Creating video series
    - Creating monthly content plans
    - Triggering video generation
    """
    
    def __init__(self, db: Session):
        """
        Initialize the video planning service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def schedule_video(
        self,
        user_id: UUID,
        suggestion_data: Dict[str, Any],
        scheduled_post_time: datetime,
        target_platforms: List[str],
        series_name: Optional[str] = None,
        series_order: Optional[int] = None,
    ) -> Video:
        """
        Schedule a single video for future generation and posting.
        
        Creates a video record with planning_status='planned'.
        The video will be generated 1 hour before scheduled_post_time.
        
        Args:
            user_id: User's UUID
            suggestion_data: Complete AI suggestion data
            scheduled_post_time: When to post the video
            target_platforms: Platforms to post to
            series_name: Series name if part of series
            series_order: Order in series
            
        Returns:
            Created Video instance
        """
        video = Video(
            id=uuid.uuid4(),
            user_id=user_id,
            title=suggestion_data.get("title"),
            prompt=suggestion_data.get("description", ""),
            status="pending",
            planning_status=PlanningStatus.PLANNED.value,
            scheduled_post_time=scheduled_post_time,
            target_platforms=target_platforms,
            ai_suggestion_data=suggestion_data,
            series_name=series_name,
            series_order=series_order,
        )
        
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        
        logger.info(f"Scheduled video {video.id} for user {user_id} at {scheduled_post_time}")
        
        return video
    
    async def create_series(
        self,
        user_id: UUID,
        series_name: str,
        videos: List[Dict[str, Any]],
        schedule: List[Dict[str, Any]],
        target_platforms: List[str],
    ) -> List[Video]:
        """
        Create a video series with multiple scheduled parts.
        
        Args:
            user_id: User's UUID
            series_name: Name of the series
            videos: List of video suggestion data
            schedule: List of schedule items with video_index and scheduled_time
            target_platforms: Platforms to post to
            
        Returns:
            List of created Video instances
        """
        created_videos = []
        
        # Create schedule lookup
        schedule_map = {
            item.get("video_index", i): item
            for i, item in enumerate(schedule)
        }
        
        for i, video_data in enumerate(videos):
            schedule_item = schedule_map.get(i, {})
            scheduled_time = schedule_item.get("scheduled_time")
            
            if isinstance(scheduled_time, str):
                scheduled_time = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            
            # Create video with series info
            video = Video(
                id=uuid.uuid4(),
                user_id=user_id,
                title=f"{series_name} - Part {i + 1}",
                prompt=video_data.get("description", ""),
                status="pending",
                planning_status=PlanningStatus.PLANNED.value,
                scheduled_post_time=scheduled_time,
                target_platforms=schedule_item.get("target_platforms") or target_platforms,
                ai_suggestion_data=video_data,
                series_name=series_name,
                series_order=i + 1,
            )
            
            self.db.add(video)
            created_videos.append(video)
        
        self.db.commit()
        
        # Refresh all videos
        for video in created_videos:
            self.db.refresh(video)
        
        logger.info(f"Created series '{series_name}' with {len(created_videos)} videos for user {user_id}")
        
        return created_videos
    
    async def create_monthly_plan(
        self,
        user_id: UUID,
        plan: Dict[str, Any],
    ) -> List[Video]:
        """
        Create a monthly content plan with multiple videos.
        
        Args:
            user_id: User's UUID
            plan: Monthly plan data
            
        Returns:
            List of created Video instances
        """
        videos_data = plan.get("videos", [])
        schedule = plan.get("schedule", [])
        target_platforms = plan.get("target_platforms", ["youtube", "tiktok", "instagram"])
        plan_type = plan.get("plan_type", "variety")
        
        created_videos = []
        
        # Create schedule lookup
        schedule_map = {
            item.get("video_index", i): item
            for i, item in enumerate(schedule)
        }
        
        # Determine series info based on plan type
        series_name = None
        if plan_type == "single_series":
            series_name = plan.get("series_info", [{}])[0].get("name", f"Series - {plan.get('month', 'Unknown')}")
        
        for i, video_data in enumerate(videos_data):
            schedule_item = schedule_map.get(i, {})
            scheduled_time = schedule_item.get("scheduled_time")
            
            if isinstance(scheduled_time, str):
                scheduled_time = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            
            # Determine title
            if series_name:
                title = f"{series_name} - Part {i + 1}"
                order = i + 1
            else:
                title = video_data.get("title", f"Video {i + 1}")
                order = None
            
            video = Video(
                id=uuid.uuid4(),
                user_id=user_id,
                title=title,
                prompt=video_data.get("description", ""),
                status="pending",
                planning_status=PlanningStatus.PLANNED.value,
                scheduled_post_time=scheduled_time,
                target_platforms=schedule_item.get("target_platforms") or target_platforms,
                ai_suggestion_data=video_data,
                series_name=series_name if plan_type == "single_series" else None,
                series_order=order,
            )
            
            self.db.add(video)
            created_videos.append(video)
        
        self.db.commit()
        
        # Refresh all videos
        for video in created_videos:
            self.db.refresh(video)
        
        logger.info(f"Created monthly plan for {plan.get('month')} with {len(created_videos)} videos for user {user_id}")
        
        return created_videos
    
    async def trigger_generation(self, video: Video) -> str:
        """
        Manually trigger generation for a planned video.
        
        Args:
            video: Video to generate
            
        Returns:
            Job ID
        """
        from app.workers.video_scheduler import queue_video_generation
        
        # Update status
        video.planning_status = PlanningStatus.GENERATING.value
        video.generation_triggered_at = datetime.utcnow()
        self.db.commit()
        
        # Queue generation job
        job_id = queue_video_generation(
            video_id=str(video.id),
            user_id=str(video.user_id),
            ai_suggestion_data=video.ai_suggestion_data,
        )
        
        if not job_id:
            # Rollback status on failure
            video.planning_status = PlanningStatus.PLANNED.value
            video.generation_triggered_at = None
            self.db.commit()
            raise Exception("Failed to queue video generation")
        
        logger.info(f"Triggered generation for video {video.id}, job {job_id}")
        
        return job_id
    
    def get_planned_videos(self, user_id: UUID) -> List[Video]:
        """Get all planned videos for a user."""
        return self.db.query(Video).filter(
            Video.user_id == user_id,
            Video.planning_status != PlanningStatus.NONE.value,
            Video.planning_status != PlanningStatus.POSTED.value,
        ).order_by(Video.scheduled_post_time.asc()).all()
    
    def get_videos_due_for_generation(self, hours_ahead: int = 1) -> List[Video]:
        """
        Get videos that need to be generated.
        
        Args:
            hours_ahead: How many hours ahead to look
            
        Returns:
            List of videos due for generation
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        
        return self.db.query(Video).filter(
            Video.planning_status == PlanningStatus.PLANNED.value,
            Video.scheduled_post_time <= cutoff,
            Video.scheduled_post_time > now,
            Video.generation_triggered_at.is_(None),
        ).all()
    
    def get_videos_ready_to_post(self) -> List[Video]:
        """Get videos that are ready to post."""
        now = datetime.utcnow()
        
        return self.db.query(Video).filter(
            Video.planning_status == PlanningStatus.READY.value,
            Video.scheduled_post_time <= now,
        ).all()


def get_video_planning_service(db: Session) -> VideoPlanningService:
    """Factory function to create a VideoPlanningService instance."""
    return VideoPlanningService(db)
