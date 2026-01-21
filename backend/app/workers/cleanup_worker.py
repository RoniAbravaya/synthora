"""
Cleanup Worker

Background worker for cleanup tasks.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.database import SessionLocal
from app.services.video import VideoService

logger = logging.getLogger(__name__)


def run_cleanup() -> Dict[str, Any]:
    """
    Run all cleanup tasks.
    
    Tasks:
    - Delete expired videos
    - Clean up orphaned jobs
    - Purge old notifications
    
    Returns:
        Dictionary with cleanup results
    """
    logger.info("Starting cleanup job")
    
    results = {
        "expired_videos": 0,
        "orphaned_jobs": 0,
        "old_notifications": 0,
    }
    
    db = SessionLocal()
    
    try:
        # Clean up expired videos
        video_service = VideoService(db)
        results["expired_videos"] = video_service.cleanup_expired_videos()
        
        # Clean up orphaned jobs (older than 7 days)
        results["orphaned_jobs"] = cleanup_orphaned_jobs(db)
        
        # Clean up old notifications (older than 30 days)
        results["old_notifications"] = cleanup_old_notifications(db)
        
        logger.info(f"Cleanup completed: {results}")
        return {
            "success": True,
            "results": results,
        }
        
    except Exception as e:
        logger.exception("Cleanup failed")
        return {
            "success": False,
            "error": str(e),
        }
        
    finally:
        db.close()


def cleanup_orphaned_jobs(db) -> int:
    """Clean up orphaned jobs older than 7 days."""
    from app.models.job import Job, JobStatus
    
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    deleted = db.query(Job).filter(
        Job.created_at < cutoff,
        Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
    ).delete(synchronize_session=False)
    
    db.commit()
    return deleted


def cleanup_old_notifications(db) -> int:
    """Clean up notifications older than 30 days."""
    from app.models.notification import Notification
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    deleted = db.query(Notification).filter(
        Notification.created_at < cutoff,
        Notification.is_read == True,
    ).delete(synchronize_session=False)
    
    db.commit()
    return deleted

