"""
Stuck Job Monitor Worker

Monitors for stuck video generation jobs and auto-cancels them.
A job is considered stuck if:
- Status is 'processing'
- last_step_updated_at is older than 30 minutes

This worker runs every 5 minutes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus, PlanningStatus
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


# Timeout threshold in minutes
STUCK_TIMEOUT_MINUTES = 30

# How often to run this check (in seconds)
CHECK_INTERVAL_SECONDS = 300  # 5 minutes


def check_stuck_jobs() -> Dict[str, Any]:
    """
    Check for stuck video generation jobs and auto-cancel them.
    
    A job is considered stuck if:
    - Status is 'processing'
    - last_step_updated_at is older than STUCK_TIMEOUT_MINUTES
    
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        timeout_threshold = now - timedelta(minutes=STUCK_TIMEOUT_MINUTES)
        
        # Find stuck videos
        stuck_videos = db.query(Video).filter(
            and_(
                Video.status == VideoStatus.PROCESSING.value,
                Video.last_step_updated_at < timeout_threshold,
                Video.last_step_updated_at.isnot(None),
            )
        ).all()
        
        results = {
            "checked_at": now.isoformat(),
            "timeout_minutes": STUCK_TIMEOUT_MINUTES,
            "stuck_count": len(stuck_videos),
            "cancelled": 0,
            "details": [],
        }
        
        for video in stuck_videos:
            try:
                # Calculate how long it's been stuck
                stuck_duration = now - video.last_step_updated_at
                stuck_minutes = stuck_duration.total_seconds() / 60
                
                logger.warning(
                    f"Found stuck video {video.id}: "
                    f"stuck at step '{video.current_step}' for {stuck_minutes:.1f} minutes"
                )
                
                # Cancel the video
                video.status = VideoStatus.CANCELLED.value
                video.error_message = (
                    f"Generation timed out after {STUCK_TIMEOUT_MINUTES} minutes "
                    f"at step: {video.current_step}"
                )
                
                # Update planning status if applicable
                if video.planning_status == PlanningStatus.GENERATING.value:
                    video.planning_status = PlanningStatus.FAILED.value
                
                db.commit()
                
                # Send notification
                _notify_timeout(db, video, stuck_minutes)
                
                results["cancelled"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "user_id": str(video.user_id),
                    "stuck_step": video.current_step,
                    "stuck_minutes": round(stuck_minutes, 1),
                    "status": "cancelled",
                })
                
            except Exception as e:
                logger.error(f"Failed to cancel stuck video {video.id}: {e}")
                results["details"].append({
                    "video_id": str(video.id),
                    "error": str(e),
                    "status": "error",
                })
        
        logger.info(f"Stuck job check completed: {results}")
        return results
        
    except Exception as e:
        logger.exception(f"Stuck job check failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def check_videos_without_updates() -> Dict[str, Any]:
    """
    Check for processing videos that never had any step updates.
    
    These are videos that were set to 'processing' but never actually
    started (e.g., worker failed to pick them up).
    
    Returns:
        Dictionary with results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Find videos processing for > 30 min without any step update
        old_processing = db.query(Video).filter(
            and_(
                Video.status == VideoStatus.PROCESSING.value,
                Video.last_step_updated_at.is_(None),
                Video.generation_started_at < now - timedelta(minutes=STUCK_TIMEOUT_MINUTES),
            )
        ).all()
        
        results = {
            "checked_at": now.isoformat(),
            "found_count": len(old_processing),
            "cancelled": 0,
        }
        
        for video in old_processing:
            try:
                video.status = VideoStatus.FAILED.value
                video.error_message = "Generation never started - worker may have failed"
                
                if video.planning_status == PlanningStatus.GENERATING.value:
                    video.planning_status = PlanningStatus.FAILED.value
                
                db.commit()
                
                _notify_never_started(db, video)
                
                results["cancelled"] += 1
                
            except Exception as e:
                logger.error(f"Failed to cancel video {video.id}: {e}")
        
        return results
        
    except Exception as e:
        logger.exception(f"Check failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def _notify_timeout(db: Session, video: Video, stuck_minutes: float) -> None:
    """Send notification about timeout."""
    try:
        notification_service = NotificationService(db)
        
        notification_service.create_notification(
            user_id=video.user_id,
            notification_type="video_generation_timeout",
            title="Video Generation Timed Out",
            message=(
                f"Your video generation timed out after {STUCK_TIMEOUT_MINUTES} minutes. "
                f"It was stuck at the '{video.current_step}' step. "
                "Please try again."
            ),
            priority="high",
            metadata={
                "video_id": str(video.id),
                "stuck_step": video.current_step,
                "stuck_minutes": round(stuck_minutes, 1),
            },
        )
    except Exception as e:
        logger.error(f"Failed to send timeout notification: {e}")


def _notify_never_started(db: Session, video: Video) -> None:
    """Send notification about generation that never started."""
    try:
        notification_service = NotificationService(db)
        
        notification_service.create_notification(
            user_id=video.user_id,
            notification_type="video_generation_failed",
            title="Video Generation Failed to Start",
            message=(
                "Your video generation failed to start. "
                "This might be a temporary system issue. Please try again."
            ),
            priority="high",
            metadata={
                "video_id": str(video.id),
                "reason": "never_started",
            },
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def get_processing_videos_summary() -> Dict[str, Any]:
    """
    Get summary of all currently processing videos.
    
    Useful for monitoring dashboard.
    
    Returns:
        Dictionary with processing video stats
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        processing_videos = db.query(Video).filter(
            Video.status == VideoStatus.PROCESSING.value
        ).all()
        
        summary = {
            "total_processing": len(processing_videos),
            "by_step": {},
            "potentially_stuck": 0,
            "healthy": 0,
        }
        
        timeout_threshold = now - timedelta(minutes=STUCK_TIMEOUT_MINUTES)
        
        for video in processing_videos:
            step = video.current_step or "unknown"
            summary["by_step"][step] = summary["by_step"].get(step, 0) + 1
            
            if video.last_step_updated_at and video.last_step_updated_at < timeout_threshold:
                summary["potentially_stuck"] += 1
            else:
                summary["healthy"] += 1
        
        return summary
        
    except Exception as e:
        logger.exception(f"Summary failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()


# =============================================================================
# Scheduler Setup
# =============================================================================

def setup_stuck_job_monitor():
    """
    Set up the stuck job monitor to run periodically.
    
    Uses RQ Scheduler to run every 5 minutes.
    """
    try:
        from rq_scheduler import Scheduler
        from redis import Redis
        from app.core.config import get_settings
        
        settings = get_settings()
        redis_conn = Redis.from_url(settings.REDIS_URL)
        scheduler = Scheduler(connection=redis_conn)
        
        # Clear existing job if present
        for job in scheduler.get_jobs():
            if hasattr(job, 'func_name') and 'check_stuck_jobs' in str(job.func_name):
                scheduler.cancel(job)
        
        # Schedule the check
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=check_stuck_jobs,
            interval=CHECK_INTERVAL_SECONDS,
            repeat=None,  # Repeat forever
            queue_name='scheduler',
        )
        
        logger.info(f"Stuck job monitor scheduled to run every {CHECK_INTERVAL_SECONDS} seconds")
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to setup stuck job monitor: {e}")
        return None
