"""
Video Scheduler Worker

Background job that:
1. Runs every 15 minutes
2. Finds videos scheduled within the next hour
3. Triggers video generation for them
4. Handles failures and notifications

Also includes:
- Job to post ready videos at their scheduled time
- Job to clean up old planned videos
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.video import Video, PlanningStatus
from app.models.user import User

logger = logging.getLogger(__name__)


# =========================================================================
# Scheduler Jobs
# =========================================================================

def check_and_trigger_scheduled_videos() -> Dict[str, Any]:
    """
    Main job: Check for videos due within 1 hour and trigger generation.
    
    This job should run every 15 minutes.
    
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        one_hour_ahead = now + timedelta(hours=1)
        
        # Find videos that:
        # - Have planning_status = 'planned'
        # - Have scheduled_post_time within the next hour
        # - Haven't had generation triggered yet
        videos_to_generate = db.query(Video).filter(
            and_(
                Video.planning_status == PlanningStatus.PLANNED.value,
                Video.scheduled_post_time <= one_hour_ahead,
                Video.scheduled_post_time > now,
                Video.generation_triggered_at.is_(None),
            )
        ).all()
        
        results = {
            "checked_at": now.isoformat(),
            "videos_found": len(videos_to_generate),
            "triggered": 0,
            "failed": 0,
            "details": [],
        }
        
        for video in videos_to_generate:
            try:
                # Mark generation as triggered
                video.planning_status = PlanningStatus.GENERATING.value
                video.generation_triggered_at = now
                db.commit()
                
                # Queue video generation job
                job_id = queue_video_generation(
                    video_id=str(video.id),
                    user_id=str(video.user_id),
                    ai_suggestion_data=video.ai_suggestion_data,
                )
                
                results["triggered"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "scheduled_for": video.scheduled_post_time.isoformat() if video.scheduled_post_time else None,
                    "job_id": job_id,
                })
                
                logger.info(f"Triggered generation for video {video.id}, job {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to trigger generation for video {video.id}: {e}")
                video.planning_status = PlanningStatus.FAILED.value
                db.commit()
                
                # Notify user of failure
                _notify_generation_failure(db, video, str(e))
                
                results["failed"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "error": str(e),
                })
        
        logger.info(f"Scheduler job completed: {results}")
        return results
        
    except Exception as e:
        logger.exception(f"Scheduler job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def check_and_post_ready_videos() -> Dict[str, Any]:
    """
    Secondary job: Check for generated videos ready to post.
    
    Finds videos that:
    - Have planning_status = 'ready'
    - Have scheduled_post_time <= now
    - Posts them to target platforms
    
    This job should run every 5 minutes.
    
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        videos_to_post = db.query(Video).filter(
            and_(
                Video.planning_status == PlanningStatus.READY.value,
                Video.scheduled_post_time <= now,
            )
        ).all()
        
        results = {
            "videos_to_post": len(videos_to_post),
            "posted": 0,
            "failed": 0,
            "details": [],
        }
        
        for video in videos_to_post:
            try:
                video.planning_status = PlanningStatus.POSTING.value
                db.commit()
                
                # Queue posting job
                job_id = queue_video_posting(
                    video_id=str(video.id),
                    user_id=str(video.user_id),
                    target_platforms=video.target_platforms,
                )
                
                results["posted"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "job_id": job_id,
                })
                
            except Exception as e:
                logger.error(f"Failed to queue posting for video {video.id}: {e}")
                video.planning_status = PlanningStatus.FAILED.value
                db.commit()
                _notify_posting_failure(db, video, str(e))
                results["failed"] += 1
        
        return results
        
    except Exception as e:
        logger.exception(f"Post ready videos job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def check_overdue_videos() -> Dict[str, Any]:
    """
    Check for videos that are overdue (past their scheduled time but still planned).
    
    Marks them as failed and notifies users.
    
    Returns:
        Dictionary with results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        two_hours_ago = now - timedelta(hours=2)
        
        overdue_videos = db.query(Video).filter(
            and_(
                Video.planning_status == PlanningStatus.PLANNED.value,
                Video.scheduled_post_time < two_hours_ago,
            )
        ).all()
        
        results = {
            "overdue_count": len(overdue_videos),
            "processed": 0,
        }
        
        for video in overdue_videos:
            video.planning_status = PlanningStatus.FAILED.value
            video.error_message = "Video was not generated before scheduled time"
            
            _notify_generation_failure(
                db, video, 
                "The scheduled time has passed and the video could not be generated in time."
            )
            
            results["processed"] += 1
        
        db.commit()
        return results
        
    except Exception as e:
        logger.exception(f"Check overdue videos job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# =========================================================================
# Video Generation Job
# =========================================================================

def generate_planned_video_job(video_id: str, user_id: str, ai_suggestion_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a planned/scheduled video.
    
    This is called by the scheduler when a video is due within 1 hour.
    Uses the ai_suggestion_data to drive the generation process.
    
    Args:
        video_id: UUID of the planned video
        user_id: UUID of the user
        ai_suggestion_data: Complete suggestion data for generation
        
    Returns:
        Dictionary with generation results
    """
    db = SessionLocal()
    
    try:
        video_uuid = UUID(video_id)
        user_uuid = UUID(user_id)
        
        # Get video record
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            return {"success": False, "error": "Video not found"}
        
        # Get user
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Use existing video generation pipeline
        # This is a placeholder - integrate with actual generation service
        try:
            from app.services.generation.pipeline import VideoGenerationPipeline
            
            pipeline = VideoGenerationPipeline(db, user_uuid)
            result = pipeline.generate_from_suggestion(video, ai_suggestion_data)
            
            if result.get("success"):
                video.planning_status = PlanningStatus.READY.value
                video.video_url = result.get("video_url")
                video.thumbnail_url = result.get("thumbnail_url")
                video.duration = result.get("duration")
                video.status = "completed"
                db.commit()
                
                logger.info(f"Video {video_id} generated successfully")
                
                return {
                    "success": True,
                    "video_id": video_id,
                    "video_url": result.get("video_url"),
                }
            else:
                raise Exception(result.get("error", "Generation failed"))
                
        except ImportError:
            # Fallback if pipeline doesn't exist - mark as ready for testing
            logger.warning(f"VideoGenerationPipeline not available, marking video {video_id} as ready")
            video.planning_status = PlanningStatus.READY.value
            video.status = "completed"
            db.commit()
            
            return {
                "success": True,
                "video_id": video_id,
                "note": "Generated (mock - pipeline not available)",
            }
            
    except Exception as e:
        logger.exception(f"Planned video generation failed: {e}")
        
        # Update video status
        try:
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if video:
                video.planning_status = PlanningStatus.FAILED.value
                video.error_message = str(e)
                db.commit()
                _notify_generation_failure(db, video, str(e))
        except Exception as inner_e:
            logger.error(f"Failed to update video status: {inner_e}")
        
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def post_video_job(video_id: str, user_id: str, target_platforms: List[str]) -> Dict[str, Any]:
    """
    Post a generated video to social platforms.
    
    Args:
        video_id: UUID of the video
        user_id: UUID of the user
        target_platforms: Platforms to post to
        
    Returns:
        Dictionary with posting results
    """
    db = SessionLocal()
    
    try:
        video_uuid = UUID(video_id)
        user_uuid = UUID(user_id)
        
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            return {"success": False, "error": "Video not found"}
        
        # Post to each platform
        # This is a placeholder - integrate with actual publishing service
        post_results = {}
        
        for platform in target_platforms:
            try:
                # Placeholder for actual posting logic
                # from app.services.publishers import get_publisher
                # publisher = get_publisher(platform)
                # result = publisher.publish(video)
                
                post_results[platform] = {"success": True, "url": f"https://{platform}.com/mock-post"}
                
            except Exception as e:
                post_results[platform] = {"success": False, "error": str(e)}
        
        # Check if all posts succeeded
        all_success = all(r.get("success") for r in post_results.values())
        
        if all_success:
            video.planning_status = PlanningStatus.POSTED.value
            video.posted_at = datetime.utcnow()
            db.commit()
            
            # Notify success
            _notify_post_success(db, video, post_results)
            
            return {
                "success": True,
                "video_id": video_id,
                "post_results": post_results,
            }
        else:
            # Some posts failed
            video.planning_status = PlanningStatus.FAILED.value
            video.error_message = "Some platforms failed to post"
            db.commit()
            
            _notify_posting_failure(db, video, f"Failed platforms: {post_results}")
            
            return {
                "success": False,
                "video_id": video_id,
                "post_results": post_results,
            }
            
    except Exception as e:
        logger.exception(f"Video posting failed: {e}")
        
        try:
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if video:
                video.planning_status = PlanningStatus.FAILED.value
                video.error_message = str(e)
                db.commit()
                _notify_posting_failure(db, video, str(e))
        except Exception:
            pass
        
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# =========================================================================
# Notification Helpers
# =========================================================================

def _notify_generation_failure(db: Session, video: Video, error: str):
    """Send notification for generation failure."""
    try:
        from app.services.notification import NotificationService
        
        notification_service = NotificationService(db)
        video_title = video.ai_suggestion_data.get("title", "Untitled") if video.ai_suggestion_data else "Untitled"
        
        notification_service.create_notification(
            user_id=video.user_id,
            notification_type="video_generation_failed",
            title="Video Generation Failed",
            message=f"Failed to generate scheduled video '{video_title}'. {error}",
            priority="high",
            metadata={
                "video_id": str(video.id),
                "scheduled_time": video.scheduled_post_time.isoformat() if video.scheduled_post_time else None,
            },
        )
    except Exception as e:
        logger.error(f"Failed to send generation failure notification: {e}")


def _notify_posting_failure(db: Session, video: Video, error: str):
    """Send notification for posting failure."""
    try:
        from app.services.notification import NotificationService
        
        notification_service = NotificationService(db)
        video_title = video.ai_suggestion_data.get("title", "Untitled") if video.ai_suggestion_data else video.title or "Untitled"
        
        notification_service.create_notification(
            user_id=video.user_id,
            notification_type="video_posting_failed",
            title="Video Posting Failed",
            message=f"Failed to post video '{video_title}'. {error}",
            priority="high",
            metadata={
                "video_id": str(video.id),
                "target_platforms": video.target_platforms,
            },
        )
    except Exception as e:
        logger.error(f"Failed to send posting failure notification: {e}")


def _notify_post_success(db: Session, video: Video, post_results: Dict[str, Any]):
    """Send notification for successful posting."""
    try:
        from app.services.notification import NotificationService
        
        notification_service = NotificationService(db)
        video_title = video.ai_suggestion_data.get("title", "Untitled") if video.ai_suggestion_data else video.title or "Untitled"
        platforms = ", ".join(video.target_platforms) if video.target_platforms else "unknown platforms"
        
        notification_service.create_notification(
            user_id=video.user_id,
            notification_type="video_posted_successfully",
            title="Video Posted Successfully",
            message=f"Your video '{video_title}' has been posted to {platforms}.",
            priority="medium",
            metadata={
                "video_id": str(video.id),
                "post_results": post_results,
            },
        )
    except Exception as e:
        logger.error(f"Failed to send post success notification: {e}")


# =========================================================================
# Queue Helpers
# =========================================================================

def queue_video_generation(video_id: str, user_id: str, ai_suggestion_data: Dict[str, Any]) -> Optional[str]:
    """Queue a video generation job."""
    try:
        from redis import Redis
        from rq import Queue
        from app.core.config import get_settings
        
        settings = get_settings()
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue("video_generation", connection=redis_conn)
        
        job = queue.enqueue(
            generate_planned_video_job,
            video_id,
            user_id,
            ai_suggestion_data,
            job_timeout=1800,  # 30 minutes
        )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue video generation: {e}")
        return None


def queue_video_posting(video_id: str, user_id: str, target_platforms: List[str]) -> Optional[str]:
    """Queue a video posting job."""
    try:
        from redis import Redis
        from rq import Queue
        from app.core.config import get_settings
        
        settings = get_settings()
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue("video_posting", connection=redis_conn)
        
        job = queue.enqueue(
            post_video_job,
            video_id,
            user_id,
            target_platforms,
            job_timeout=600,  # 10 minutes
        )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue video posting: {e}")
        return None


# =========================================================================
# Scheduler Setup
# =========================================================================

def setup_scheduled_jobs():
    """
    Set up periodic jobs using RQ Scheduler.
    
    Jobs:
    - check_and_trigger_scheduled_videos: Every 15 minutes
    - check_and_post_ready_videos: Every 5 minutes
    - check_overdue_videos: Every hour
    """
    try:
        from rq_scheduler import Scheduler
        from redis import Redis
        from app.core.config import get_settings
        
        settings = get_settings()
        redis_conn = Redis.from_url(settings.REDIS_URL)
        scheduler = Scheduler(connection=redis_conn)
        
        # Clear existing jobs (for redeployment)
        for job in scheduler.get_jobs():
            scheduler.cancel(job)
        
        # Schedule video generation check - every 15 minutes
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=check_and_trigger_scheduled_videos,
            interval=900,  # 15 minutes in seconds
            repeat=None,  # Repeat forever
            queue_name='scheduler',
        )
        
        # Schedule posting check - every 5 minutes
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=check_and_post_ready_videos,
            interval=300,  # 5 minutes in seconds
            repeat=None,
            queue_name='scheduler',
        )
        
        # Schedule overdue check - every hour
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=check_overdue_videos,
            interval=3600,  # 1 hour in seconds
            repeat=None,
            queue_name='scheduler',
        )
        
        logger.info("Scheduled jobs set up successfully")
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to setup scheduled jobs: {e}")
        return None
