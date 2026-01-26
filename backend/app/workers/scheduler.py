"""
Job Scheduler

Handles scheduling and enqueueing background jobs.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# Optional Redis/RQ imports - only loaded if Redis is available
_redis_available = False
Redis = None
Queue = None
RQJob = None

try:
    from redis import Redis as RedisClient
    from rq import Queue as RQQueue
    from rq.job import Job as RQJobClass
    Redis = RedisClient
    Queue = RQQueue
    RQJob = RQJobClass
    _redis_available = True
except ImportError:
    logger.warning("Redis/RQ not available - background jobs disabled")


class JobScheduler:
    """
    Manages background job scheduling using RQ.
    
    Queues:
    - default: General tasks
    - video: Video generation tasks
    - analytics: Analytics sync tasks
    - posts: Scheduled post tasks
    - cleanup: Cleanup tasks
    
    If Redis is not configured, jobs run synchronously.
    """
    
    QUEUES = ["default", "video", "analytics", "posts", "cleanup"]
    
    def __init__(self):
        """Initialize the job scheduler."""
        settings = get_settings()
        
        self.redis = None
        self.queues = {}
        self._redis_available = False
        
        # Check if Redis URL is configured and valid
        redis_url = settings.REDIS_URL
        if redis_url and _redis_available and not self._is_placeholder_url(redis_url):
            try:
                self.redis = Redis.from_url(redis_url)
                # Test connection
                self.redis.ping()
                self._redis_available = True
                
                # Create queues
                self.queues = {
                    name: Queue(name, connection=self.redis)
                    for name in self.QUEUES
                }
                logger.info("Redis connected - background jobs enabled")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e} - jobs will run synchronously")
                self.redis = None
                self._redis_available = False
        else:
            logger.info("Redis not configured - jobs will run synchronously")
    
    def _is_placeholder_url(self, url: str) -> bool:
        """Check if the URL is a placeholder that shouldn't be used."""
        if not url:
            return True
        placeholders = ["your-endpoint", "placeholder", "example.com", "localhost:6379"]
        return any(p in url.lower() for p in placeholders)
    
    def enqueue_video_generation(
        self,
        video_id: UUID,
        user_id: UUID,
        prompt: str,
        template_id: Optional[UUID] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Enqueue a video generation job.
        
        Args:
            video_id: Video UUID
            user_id: User UUID
            prompt: Video prompt
            template_id: Optional template UUID
            config_overrides: Optional configuration overrides
            
        Returns:
            RQ Job instance, or None if running synchronously
        """
        from app.workers.video_worker import process_video_generation
        
        if self._redis_available and "video" in self.queues:
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
        else:
            # Run synchronously (for development/demo without Redis)
            logger.info(f"Running video generation synchronously for video {video_id}")
            try:
                import threading
                # Run in background thread to not block the request
                thread = threading.Thread(
                    target=process_video_generation,
                    kwargs={
                        "video_id": str(video_id),
                        "user_id": str(user_id),
                        "prompt": prompt,
                        "template_id": str(template_id) if template_id else None,
                        "config_overrides": config_overrides,
                    },
                    daemon=True
                )
                thread.start()
                logger.info(f"Started background thread for video {video_id}")
            except Exception as e:
                logger.error(f"Failed to start video generation: {e}")
            return None
    
    def enqueue_video_retry(
        self,
        video_id: UUID,
        swap_integration: Optional[Dict[str, str]] = None,
    ) -> Optional[Any]:
        """
        Enqueue a video retry job.
        
        Args:
            video_id: Video UUID
            swap_integration: Optional integration swaps
            
        Returns:
            RQ Job instance, or None if running synchronously
        """
        from app.workers.video_worker import retry_video_generation
        
        if self._redis_available and "video" in self.queues:
            job = self.queues["video"].enqueue(
                retry_video_generation,
                video_id=str(video_id),
                swap_integration=swap_integration,
                job_timeout="30m",
                result_ttl=86400,
            )
            
            logger.info(f"Enqueued video retry job: {job.id} for video {video_id}")
            return job
        else:
            # Run synchronously
            logger.info(f"Running video retry synchronously for video {video_id}")
            try:
                import threading
                thread = threading.Thread(
                    target=retry_video_generation,
                    kwargs={
                        "video_id": str(video_id),
                        "swap_integration": swap_integration,
                    },
                    daemon=True
                )
                thread.start()
            except Exception as e:
                logger.error(f"Failed to start video retry: {e}")
            return None
    
    def enqueue_analytics_sync(
        self,
        user_id: UUID,
        platform: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Enqueue an analytics sync job.
        
        Args:
            user_id: User UUID
            platform: Optional specific platform to sync
            
        Returns:
            RQ Job instance, or None if Redis not available
        """
        if not self._redis_available or "analytics" not in self.queues:
            logger.warning("Redis not available - skipping analytics sync")
            return None
            
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
    ) -> Optional[Any]:
        """
        Enqueue a scheduled post job.
        
        Args:
            post_id: Post UUID
            scheduled_time: When to publish
            
        Returns:
            RQ Job instance, or None if Redis not available
        """
        if not self._redis_available or "posts" not in self.queues:
            logger.warning("Redis not available - cannot schedule post")
            return None
            
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
    
    def enqueue_cleanup(self) -> Optional[Any]:
        """
        Enqueue a cleanup job.
        
        Returns:
            RQ Job instance, or None if Redis not available
        """
        if not self._redis_available or "cleanup" not in self.queues:
            logger.warning("Redis not available - skipping cleanup job")
            return None
            
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
        if not self._redis_available or RQJob is None:
            return None
            
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
        if not self._redis_available or RQJob is None:
            return False
            
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
        if not self._redis_available:
            return {name: {"pending": 0, "started": 0, "finished": 0, "failed": 0} for name in self.QUEUES}
            
        stats = {}
        
        for name, queue in self.queues.items():
            stats[name] = {
                "pending": len(queue),
                "started": queue.started_job_registry.count,
                "finished": queue.finished_job_registry.count,
                "failed": queue.failed_job_registry.count,
            }
        
        return stats
    
    @property
    def is_redis_available(self) -> bool:
        """Check if Redis is available for background jobs."""
        return self._redis_available


# Global scheduler instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get the global job scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = JobScheduler()
    
    return _scheduler

