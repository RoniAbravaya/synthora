"""
Job Scheduler

Handles scheduling and enqueueing background jobs.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from redis import Redis
from rq import Queue
from rq.job import Job as RQJob

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Manages background job scheduling using RQ.
    
    Queues:
    - default: General tasks
    - video: Video generation tasks
    - analytics: Analytics sync tasks
    - posts: Scheduled post tasks
    - cleanup: Cleanup tasks
    """
    
    QUEUES = ["default", "video", "analytics", "posts", "cleanup"]
    
    def __init__(self):
        """Initialize the job scheduler."""
        settings = get_settings()
        
        self.redis = Redis.from_url(settings.REDIS_URL)
        
        # Create queues
        self.queues = {
            name: Queue(name, connection=self.redis)
            for name in self.QUEUES
        }
    
    def enqueue_video_generation(
        self,
        video_id: UUID,
        user_id: UUID,
        prompt: str,
        template_id: Optional[UUID] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> RQJob:
        """
        Enqueue a video generation job.
        
        Args:
            video_id: Video UUID
            user_id: User UUID
            prompt: Video prompt
            template_id: Optional template UUID
            config_overrides: Optional configuration overrides
            
        Returns:
            RQ Job instance
        """
        from app.workers.video_worker import process_video_generation
        
        job = self.queues["video"].enqueue(
            process_video_generation,
            video_id=str(video_id),
            user_id=str(user_id),
            prompt=prompt,
            template_id=str(template_id) if template_id else None,
            config_overrides=config_overrides,
            job_timeout="30m",  # 30 minute timeout
            result_ttl=86400,   # Keep result for 24 hours
        )
        
        logger.info(f"Enqueued video generation job: {job.id} for video {video_id}")
        return job
    
    def enqueue_video_retry(
        self,
        video_id: UUID,
        swap_integration: Optional[Dict[str, str]] = None,
    ) -> RQJob:
        """
        Enqueue a video retry job.
        
        Args:
            video_id: Video UUID
            swap_integration: Optional integration swaps
            
        Returns:
            RQ Job instance
        """
        from app.workers.video_worker import retry_video_generation
        
        job = self.queues["video"].enqueue(
            retry_video_generation,
            video_id=str(video_id),
            swap_integration=swap_integration,
            job_timeout="30m",
            result_ttl=86400,
        )
        
        logger.info(f"Enqueued video retry job: {job.id} for video {video_id}")
        return job
    
    def enqueue_analytics_sync(
        self,
        user_id: UUID,
        platform: Optional[str] = None,
    ) -> RQJob:
        """
        Enqueue an analytics sync job.
        
        Args:
            user_id: User UUID
            platform: Optional specific platform to sync
            
        Returns:
            RQ Job instance
        """
        from app.workers.analytics_worker import sync_analytics
        
        job = self.queues["analytics"].enqueue(
            sync_analytics,
            user_id=str(user_id),
            platform=platform,
            job_timeout="10m",
            result_ttl=3600,
        )
        
        logger.info(f"Enqueued analytics sync job: {job.id}")
        return job
    
    def enqueue_scheduled_post(
        self,
        post_id: UUID,
        scheduled_time: datetime,
    ) -> RQJob:
        """
        Enqueue a scheduled post job.
        
        Args:
            post_id: Post UUID
            scheduled_time: When to publish
            
        Returns:
            RQ Job instance
        """
        from app.workers.post_worker import publish_scheduled_post
        
        # Calculate delay
        delay = (scheduled_time - datetime.utcnow()).total_seconds()
        
        if delay <= 0:
            # Publish immediately
            job = self.queues["posts"].enqueue(
                publish_scheduled_post,
                post_id=str(post_id),
                job_timeout="5m",
                result_ttl=3600,
            )
        else:
            # Schedule for later
            job = self.queues["posts"].enqueue_at(
                scheduled_time,
                publish_scheduled_post,
                post_id=str(post_id),
                job_timeout="5m",
                result_ttl=3600,
            )
        
        logger.info(f"Scheduled post job: {job.id} for {scheduled_time}")
        return job
    
    def enqueue_cleanup(self) -> RQJob:
        """
        Enqueue a cleanup job.
        
        Returns:
            RQ Job instance
        """
        from app.workers.cleanup_worker import run_cleanup
        
        job = self.queues["cleanup"].enqueue(
            run_cleanup,
            job_timeout="15m",
            result_ttl=3600,
        )
        
        logger.info(f"Enqueued cleanup job: {job.id}")
        return job
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job.
        
        Args:
            job_id: RQ Job ID
            
        Returns:
            Job status dictionary, or None if not found
        """
        try:
            job = RQJob.fetch(job_id, connection=self.redis)
            
            return {
                "id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "meta": job.meta,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: RQ Job ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            job = RQJob.fetch(job_id, connection=self.redis)
            job.cancel()
            logger.info(f"Cancelled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for all queues.
        
        Returns:
            Dictionary with queue statistics
        """
        stats = {}
        
        for name, queue in self.queues.items():
            stats[name] = {
                "pending": len(queue),
                "started": queue.started_job_registry.count,
                "finished": queue.finished_job_registry.count,
                "failed": queue.failed_job_registry.count,
            }
        
        return stats


# Global scheduler instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get the global job scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = JobScheduler()
    
    return _scheduler

