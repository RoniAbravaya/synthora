"""
Analytics Worker

Background jobs for fetching and syncing analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session
from rq import get_current_job

from app.core.database import SessionLocal
from app.core.security import decrypt_token
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.analytics import Analytics, AnalyticsPlatform
from app.services.analytics import AnalyticsService
from app.services.analytics_fetchers import get_fetcher

logger = logging.getLogger(__name__)


# =========================================================================
# Platform Mapping
# =========================================================================

SOCIAL_TO_ANALYTICS_PLATFORM = {
    SocialPlatform.YOUTUBE: AnalyticsPlatform.YOUTUBE,
    SocialPlatform.TIKTOK: AnalyticsPlatform.TIKTOK,
    SocialPlatform.INSTAGRAM: AnalyticsPlatform.INSTAGRAM,
    SocialPlatform.FACEBOOK: AnalyticsPlatform.FACEBOOK,
}


# =========================================================================
# Analytics Sync Jobs
# =========================================================================

def sync_post_analytics_job(post_id: str) -> dict:
    """
    Sync analytics for a specific post across all platforms.
    
    Args:
        post_id: Post UUID string
        
    Returns:
        Dictionary with sync results
    """
    job = get_current_job()
    db = SessionLocal()
    
    try:
        post_uuid = UUID(post_id)
        
        # Get the post
        post = db.query(Post).filter(Post.id == post_uuid).first()
        
        if not post:
            return {"success": False, "error": "Post not found"}
        
        if post.status != PostStatus.PUBLISHED:
            return {"success": False, "error": "Post not published"}
        
        analytics_service = AnalyticsService(db)
        results = {}
        
        # Sync each platform
        for platform_name, platform_post_id in (post.platform_post_ids or {}).items():
            if not platform_post_id:
                continue
            
            try:
                # Get social account for this platform
                social_platform = SocialPlatform(platform_name)
                social_account = db.query(SocialAccount).filter(
                    SocialAccount.user_id == post.user_id,
                    SocialAccount.platform == social_platform,
                    SocialAccount.is_active == True,
                ).first()
                
                if not social_account:
                    results[platform_name] = {"success": False, "error": "No connected account"}
                    continue
                
                # Decrypt access token
                access_token = decrypt_token(social_account.access_token_encrypted)
                refresh_token = None
                if social_account.refresh_token_encrypted:
                    refresh_token = decrypt_token(social_account.refresh_token_encrypted)
                
                # Get fetcher
                fetcher_class = get_fetcher(platform_name)
                fetcher = fetcher_class(access_token, refresh_token)
                
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
                    # Store analytics
                    analytics_platform = SOCIAL_TO_ANALYTICS_PLATFORM[social_platform]
                    
                    analytics_service.store_analytics(
                        post_id=post_uuid,
                        platform=analytics_platform,
                        platform_post_id=platform_post_id,
                        views=fetch_result.views,
                        likes=fetch_result.likes,
                        comments=fetch_result.comments,
                        shares=fetch_result.shares,
                        saves=fetch_result.saves,
                        watch_time_seconds=fetch_result.watch_time_seconds,
                        avg_view_duration=fetch_result.avg_view_duration,
                        reach=fetch_result.reach,
                        impressions=fetch_result.impressions,
                        click_through_rate=fetch_result.click_through_rate,
                        follower_change=fetch_result.follower_change,
                        raw_data=fetch_result.raw_data,
                    )
                    
                    results[platform_name] = {
                        "success": True,
                        "views": fetch_result.views,
                        "likes": fetch_result.likes,
                    }
                else:
                    results[platform_name] = {
                        "success": False,
                        "error": fetch_result.error,
                    }
                    
            except Exception as e:
                logger.error(f"Failed to sync analytics for {platform_name}: {e}")
                results[platform_name] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "post_id": post_id,
            "results": results,
        }
        
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
        
        # Get all published posts
        posts = db.query(Post).filter(
            Post.user_id == user_uuid,
            Post.status == PostStatus.PUBLISHED,
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
        # Get all users with published posts
        from app.models.user import User
        
        users_with_posts = db.query(User.id).join(Post).filter(
            Post.status == PostStatus.PUBLISHED,
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
                platform_name = account.platform.value
                
                # Decrypt tokens
                access_token = decrypt_token(account.access_token_encrypted)
                refresh_token = None
                if account.refresh_token_encrypted:
                    refresh_token = decrypt_token(account.refresh_token_encrypted)
                
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
                results[account.platform.value] = {"error": str(e)}
        
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

def queue_analytics_sync(post_id: UUID, queue_name: str = "analytics") -> Optional[str]:
    """
    Queue an analytics sync job for a post.
    
    Args:
        post_id: Post UUID
        queue_name: Name of the queue
        
    Returns:
        Job ID if queued successfully
    """
    try:
        from redis import Redis
        from rq import Queue
        from app.core.config import settings
        
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue(queue_name, connection=redis_conn)
        
        job = queue.enqueue(
            sync_post_analytics_job,
            str(post_id),
            job_timeout=300,  # 5 minutes
        )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue analytics sync: {e}")
        return None


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
        from app.core.config import settings
        
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

