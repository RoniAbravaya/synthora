"""
Analytics Worker

Background jobs for fetching and syncing analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session
from rq import get_current_job

from app.core.database import SessionLocal
from app.core.security import decrypt_value
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.analytics import Analytics
from app.services.analytics import AnalyticsService
from app.services.analytics_fetchers import get_fetcher

logger = logging.getLogger(__name__)


# =========================================================================
# Analytics Sync Jobs
# =========================================================================

def sync_post_analytics_job(post_id: str) -> dict:
    """
    Sync analytics for a specific post.
    
    Each post is linked to one platform and one social account.
    
    Args:
        post_id: Post UUID string
        
    Returns:
        Dictionary with sync results
    """
    logger.info(f"=== ANALYTICS SYNC JOB STARTED for post {post_id} ===")
    
    job = get_current_job()
    db = SessionLocal()
    
    try:
        post_uuid = UUID(post_id)
        
        # Get the post
        post = db.query(Post).filter(Post.id == post_uuid).first()
        
        if not post:
            logger.error(f"Analytics sync: Post {post_id} not found")
            return {"success": False, "error": "Post not found"}
        
        # Use string comparison
        if post.status != "published":
            return {"success": False, "error": "Post not published"}
        
        # Get the platform post ID (stored after successful publish)
        platform_post_id = post.platform_post_id
        if not platform_post_id:
            return {"success": False, "error": "No platform post ID (post may not be fully published)"}
        
        platform_name = post.platform
        
        analytics_service = AnalyticsService(db)
        
        try:
            # Get the social account for this post
            social_account = db.query(SocialAccount).filter(
                SocialAccount.id == post.social_account_id,
                SocialAccount.is_active == True,
            ).first()
            
            if not social_account:
                logger.error(f"Analytics sync: No connected account found for post {post_id}")
                return {"success": False, "error": "No connected account found"}
            
            logger.info(f"Analytics sync: Found social account {social_account.id} for {platform_name}")
            logger.info(f"Analytics sync: Platform post ID = {platform_post_id}")
            
            # Decrypt access token
            access_token = decrypt_value(social_account.access_token_encrypted)
            refresh_token = None
            if social_account.refresh_token_encrypted:
                refresh_token = decrypt_value(social_account.refresh_token_encrypted)
            
            logger.info(f"Analytics sync: Access token decrypted (length={len(access_token) if access_token else 0})")
            
            # Get fetcher
            fetcher_class = get_fetcher(platform_name)
            fetcher = fetcher_class(access_token, refresh_token)
            
            logger.info(f"Analytics sync: Calling {platform_name} API to fetch analytics...")
            
            # Fetch analytics (run async in sync context)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                fetch_result = loop.run_until_complete(
                    fetcher.fetch_video_analytics(platform_post_id)
                )
            finally:
                loop.close()
            
                if fetch_result.success:
                    # Log information about the fetched data
                    logger.info(f"=== ANALYTICS FETCH SUCCESSFUL for post {post_id} ===")
                    logger.info(
                        f"Analytics fetch successful for post {post_id}: "
                        f"views={fetch_result.views}, likes={fetch_result.likes}, "
                        f"comments={fetch_result.comments}, shares={fetch_result.shares}"
                    )
                
                # Warn if all metrics are 0 (common for newly published posts)
                if (fetch_result.views == 0 and fetch_result.likes == 0 and 
                    fetch_result.comments == 0 and fetch_result.shares == 0):
                    logger.warning(
                        f"All metrics are 0 for post {post_id} on {platform_name}. "
                        "This is normal for newly published posts. Platforms like YouTube "
                        "can take 24-48 hours to fully report engagement metrics. "
                        "Additional syncs are scheduled automatically."
                    )
                
                # Store analytics
                analytics_service.store_analytics(
                    post_id=post_uuid,
                    user_id=post.user_id,
                    platform=platform_name,
                    views=fetch_result.views,
                    likes=fetch_result.likes,
                    comments=fetch_result.comments,
                    shares=fetch_result.shares,
                    saves=fetch_result.saves,
                    watch_time_seconds=fetch_result.watch_time_seconds,
                    avg_watch_percentage=fetch_result.retention_rate,
                    reach=fetch_result.reach,
                    impressions=fetch_result.impressions,
                    clicks=0,  # YouTube doesn't have clicks
                    raw_data=fetch_result.raw_data,
                )
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "platform": platform_name,
                    "views": fetch_result.views,
                    "likes": fetch_result.likes,
                    "comments": fetch_result.comments,
                    "shares": fetch_result.shares,
                    "note": "Analytics may update over time as platforms report data" if 
                           fetch_result.views == 0 else None,
                }
            else:
                logger.error(f"Analytics fetch failed for post {post_id}: {fetch_result.error}")
                return {
                    "success": False,
                    "error": fetch_result.error,
                }
                
        except Exception as e:
            logger.error(f"Failed to sync analytics for {platform_name}: {e}")
            return {"success": False, "error": str(e)}
        
    except Exception as e:
        logger.exception(f"Analytics sync job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def sync_user_analytics_job(user_id: str) -> dict:
    """
    Sync analytics for all published posts of a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with sync results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        # Get all published posts (use string comparison)
        posts = db.query(Post).filter(
            Post.user_id == user_uuid,
            Post.status == "published",
        ).all()
        
        results = {
            "total_posts": len(posts),
            "synced": 0,
            "failed": 0,
            "errors": [],
        }
        
        for post in posts:
            try:
                result = sync_post_analytics_job(str(post.id))
                if result.get("success"):
                    results["synced"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "post_id": str(post.id),
                        "error": result.get("error"),
                    })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "post_id": str(post.id),
                    "error": str(e),
                })
        
        return {
            "success": True,
            "user_id": user_id,
            **results,
        }
        
    except Exception as e:
        logger.exception(f"User analytics sync job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def daily_analytics_sync_job() -> dict:
    """
    Daily job to sync analytics for all users.
    
    This job should be scheduled to run once per day.
    
    Returns:
        Dictionary with sync results
    """
    db = SessionLocal()
    
    try:
        # Get all users with published posts (use string comparison)
        from app.models.user import User
        
        users_with_posts = db.query(User.id).join(Post).filter(
            Post.status == "published",
        ).distinct().all()
        
        results = {
            "total_users": len(users_with_posts),
            "synced": 0,
            "failed": 0,
        }
        
        for (user_id,) in users_with_posts:
            try:
                result = sync_user_analytics_job(str(user_id))
                if result.get("success"):
                    results["synced"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to sync analytics for user {user_id}: {e}")
                results["failed"] += 1
        
        logger.info(f"Daily analytics sync completed: {results}")
        return {
            "success": True,
            **results,
        }
        
    except Exception as e:
        logger.exception(f"Daily analytics sync job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def sync_channel_analytics_job(user_id: str) -> dict:
    """
    Sync channel/account-level analytics for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with channel analytics
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        # Get all connected social accounts
        accounts = db.query(SocialAccount).filter(
            SocialAccount.user_id == user_uuid,
            SocialAccount.is_active == True,
        ).all()
        
        results = {}
        
        for account in accounts:
            try:
                # Platform is now stored as string
                platform_name = account.platform
                
                # Decrypt tokens
                access_token = decrypt_value(account.access_token_encrypted)
                refresh_token = None
                if account.refresh_token_encrypted:
                    refresh_token = decrypt_value(account.refresh_token_encrypted)
                
                # Get fetcher
                fetcher_class = get_fetcher(platform_name)
                fetcher = fetcher_class(access_token, refresh_token)
                
                # Fetch channel analytics
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    channel_data = loop.run_until_complete(
                        fetcher.fetch_channel_analytics()
                    )
                finally:
                    loop.close()
                
                results[platform_name] = channel_data
                
            except Exception as e:
                logger.error(f"Failed to fetch channel analytics for {account.platform}: {e}")
                results[account.platform] = {"error": str(e)}
        
        return {
            "success": True,
            "user_id": user_id,
            "channels": results,
        }
        
    except Exception as e:
        logger.exception(f"Channel analytics sync job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# =========================================================================
# Queue Helpers
# =========================================================================

def queue_analytics_sync(
    post_id: UUID, 
    queue_name: str = "analytics",
    delay_seconds: int = 0,
) -> Optional[str]:
    """
    Queue an analytics sync job for a post.
    
    Args:
        post_id: Post UUID
        queue_name: Name of the queue
        delay_seconds: Delay in seconds before executing the job (default: 0 = immediate)
        
    Returns:
        Job ID if queued successfully
    """
    logger.info(f"=== QUEUEING ANALYTICS SYNC for post {post_id}, delay={delay_seconds}s ===")
    
    try:
        from redis import Redis
        from rq import Queue
        from app.core.config import get_settings
        from datetime import timedelta
        
        settings = get_settings()
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured, skipping analytics queue")
            return None
        
        logger.info(f"Connecting to Redis for analytics queue...")
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue(queue_name, connection=redis_conn)
        logger.info(f"Redis connection established, queue={queue_name}")
        
        if delay_seconds > 0:
            # Schedule with delay
            logger.info(f"Scheduling analytics sync for post {post_id} with {delay_seconds}s delay")
            job = queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                sync_post_analytics_job,
                str(post_id),
                job_timeout=300,  # 5 minutes
            )
        else:
            # Immediate execution
            job = queue.enqueue(
                sync_post_analytics_job,
                str(post_id),
                job_timeout=300,  # 5 minutes
            )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue analytics sync: {e}")
        return None


def schedule_analytics_sync_sequence(post_id: UUID) -> List[Optional[str]]:
    """
    Schedule a sequence of analytics sync jobs for a newly published post.
    
    YouTube and other platforms have delays in reporting statistics,
    so we schedule multiple syncs over time to capture accurate data:
    - Immediately (basic check)
    - After 1 hour (basic stats should be available)
    - After 6 hours (more accurate stats)
    - After 24 hours (stable stats)
    - After 48 hours (detailed analytics available)
    
    Args:
        post_id: Post UUID
        
    Returns:
        List of job IDs (None for failed queues)
    """
    delays = [
        0,          # Immediate
        3600,       # 1 hour
        21600,      # 6 hours
        86400,      # 24 hours
        172800,     # 48 hours
    ]
    
    job_ids = []
    for delay in delays:
        job_id = queue_analytics_sync(post_id, delay_seconds=delay)
        job_ids.append(job_id)
        if delay == 0:
            logger.info(f"Scheduled immediate analytics sync for post {post_id}")
        else:
            hours = delay // 3600
            logger.info(f"Scheduled analytics sync for post {post_id} in {hours} hour(s)")
    
    return job_ids


def queue_user_analytics_sync(user_id: UUID, queue_name: str = "analytics") -> Optional[str]:
    """
    Queue an analytics sync job for all user posts.
    
    Args:
        user_id: User UUID
        queue_name: Name of the queue
        
    Returns:
        Job ID if queued successfully
    """
    try:
        from redis import Redis
        from rq import Queue
        from app.core.config import get_settings
        
        settings = get_settings()
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured, skipping analytics queue")
            return None
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue(queue_name, connection=redis_conn)
        
        job = queue.enqueue(
            sync_user_analytics_job,
            str(user_id),
            job_timeout=1800,  # 30 minutes
        )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue user analytics sync: {e}")
        return None
