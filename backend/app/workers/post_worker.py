"""
Post Worker

Background worker for publishing posts to social media platforms.
"""

import logging
import asyncio
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.post import PostService
from app.services.social_oauth import SocialOAuthService
from app.services.publishers import get_publisher
from app.services.publishers.base import PublishRequest
from app.models.post import Post, PostStatus
from app.models.video import Video
from app.models.social_account import SocialAccount, SocialPlatform

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get a database session for the worker."""
    return SessionLocal()


def publish_scheduled_post(post_id: str) -> Dict[str, Any]:
    """
    Publish a scheduled post.
    
    This is the main entry point for scheduled post workers.
    
    Args:
        post_id: UUID of the post to publish
        
    Returns:
        Dictionary with publish results
    """
    logger.info(f"Publishing scheduled post: {post_id}")
    
    db = get_db()
    
    try:
        post_service = PostService(db)
        post = post_service.get_by_id(UUID(post_id))
        
        if not post:
            logger.error(f"Post not found: {post_id}")
            return {"success": False, "error": "Post not found"}
        
        # Check if post is still scheduled (use string comparison)
        if post.status != "scheduled":
            logger.warning(f"Post {post_id} is not scheduled (status: {post.status})")
            return {"success": False, "error": f"Post status is {post.status}"}
        
        # Run the async publish
        result = asyncio.run(_publish_post(db, post))
        
        return result
        
    except Exception as e:
        logger.exception(f"Error publishing post {post_id}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def publish_post_now(post_id: str) -> Dict[str, Any]:
    """
    Publish a post immediately.
    
    Args:
        post_id: UUID of the post to publish
        
    Returns:
        Dictionary with publish results
    """
    logger.info(f"=== PUBLISH POST NOW STARTED: {post_id} ===")
    
    db = get_db()
    
    try:
        post_service = PostService(db)
        post = post_service.get_by_id(UUID(post_id))
        
        if not post:
            logger.error(f"Post not found: {post_id}")
            return {"success": False, "error": "Post not found"}
        
        logger.info(f"Post found: id={post.id}, platform={post.platform}, status={post.status}, video_id={post.video_id}")
        
        # Allow draft, scheduled, or publishing status
        # (publishing is set by the API endpoint before queuing)
        if post.status not in ["draft", "scheduled", "publishing"]:
            logger.warning(f"Cannot publish post {post_id} in status: {post.status}")
            return {"success": False, "error": f"Cannot publish post in status: {post.status}"}
        
        logger.info(f"Publishing post {post_id} to {post.platform} (current status: {post.status})")
        result = asyncio.run(_publish_post(db, post))
        
        logger.info(f"=== PUBLISH RESULT for {post_id}: {result} ===")
        return result
        
    except Exception as e:
        logger.exception(f"=== PUBLISH ERROR for {post_id}: {e} ===")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


async def _publish_post(db: Session, post: Post) -> Dict[str, Any]:
    """
    Internal function to publish a post to its target platform.
    
    Each post is linked to one platform and one social account.
    
    Args:
        db: Database session
        post: Post to publish
        
    Returns:
        Dictionary with results
    """
    from app.workers.analytics_worker import schedule_analytics_sync_sequence
    
    logger.info(f"_publish_post: Starting for post {post.id} to platform {post.platform}")
    
    post_service = PostService(db)
    oauth_service = SocialOAuthService(db)
    
    # Mark post as publishing
    post.status = "publishing"
    db.commit()
    logger.info(f"_publish_post: Status set to publishing")
    
    # Get video
    video = db.query(Video).filter(Video.id == post.video_id).first()
    if not video:
        logger.error(f"_publish_post: Video {post.video_id} not found")
        post.mark_failed("Video not found")
        db.commit()
        return {"success": False, "error": "Video not found"}
    
    logger.info(f"_publish_post: Video found - title='{video.title}', status={video.status}, url={video.video_url[:100] if video.video_url else 'None'}...")
    
    # Get the social account linked to this post
    account = db.query(SocialAccount).filter(
        SocialAccount.id == post.social_account_id
    ).first()
    
    if not account:
        logger.error(f"_publish_post: Social account {post.social_account_id} not found")
        post.mark_failed("Social account not found")
        db.commit()
        return {"success": False, "error": "Social account not found"}
    
    logger.info(f"_publish_post: Social account found - platform={account.platform}, username={account.username}, status={account.status}")
    
    # Get access token
    access_token = oauth_service.get_access_token(account)
    
    if not access_token:
        logger.error(f"_publish_post: Failed to get access token for account {account.id}")
        post.mark_failed("Failed to get access token")
        db.commit()
        return {"success": False, "error": "Failed to get access token"}
    
    logger.info(f"_publish_post: Access token retrieved (length={len(access_token)})")
    
    # Get platform-specific overrides from platform_config
    platform_overrides = post.platform_config or {}
    
    # Create publish request
    request = PublishRequest(
        video_path=video.video_url or "",  # Local path or URL
        video_url=video.video_url,  # Public URL for Instagram
        title=video.title or "Untitled",
        description=post.caption or "",
        hashtags=post.hashtags or [],
        access_token=access_token,
        platform_overrides=platform_overrides,
    )
    
    logger.info(f"_publish_post: PublishRequest created - title='{request.title}', hashtags={len(request.hashtags)}, video_path={request.video_path[:100] if request.video_path else 'None'}...")
    
    # Get publisher and publish
    try:
        platform_enum = SocialPlatform(post.platform)
        publisher = get_publisher(platform_enum)
        logger.info(f"_publish_post: Got publisher for {platform_enum}")
        
        logger.info(f"_publish_post: Starting publish to {post.platform}...")
        result = await publisher.publish(request)
        logger.info(f"_publish_post: Publish completed - success={result.success}, post_id={result.post_id}, error={result.error}")
        
        if result.success:
            post.mark_published(result.post_id, result.post_url)
            db.commit()
            logger.info(f"_publish_post: Post marked as published, post_url={result.post_url}")
            
            # Schedule a sequence of analytics syncs over time
            # This is important because platforms like YouTube have delays
            # in reporting statistics (can take hours to days for full data)
            try:
                job_ids = schedule_analytics_sync_sequence(post.id)
                scheduled_count = sum(1 for j in job_ids if j is not None)
                logger.info(
                    f"Scheduled {scheduled_count} analytics sync jobs for post {post.id}. "
                    "Note: YouTube stats may take 24-48 hours to fully populate."
                )
            except Exception as e:
                logger.warning(f"Failed to schedule analytics sync sequence: {e}")
            
            return {
                "success": True,
                "post_id": str(post.id),
                "platform": post.platform,
                "platform_post_id": result.post_id,
                "post_url": result.post_url,
            }
        else:
            logger.error(f"_publish_post: Publisher returned failure - {result.error}")
            post.mark_failed(result.error)
            db.commit()
            return {
                "success": False,
                "post_id": str(post.id),
                "platform": post.platform,
                "error": result.error,
            }
            
    except Exception as e:
        logger.exception(f"_publish_post: Exception publishing to {post.platform}: {e}")
        post.mark_failed(str(e))
        db.commit()
        return {
            "success": False,
            "post_id": str(post.id),
            "platform": post.platform,
            "error": str(e),
        }


def process_scheduled_posts() -> Dict[str, Any]:
    """
    Process all pending scheduled posts.
    
    This job should run periodically (e.g., every minute).
    
    Returns:
        Dictionary with processing results
    """
    logger.info("Processing scheduled posts")
    
    db = get_db()
    
    try:
        post_service = PostService(db)
        pending_posts = post_service.get_pending_scheduled_posts(limit=10)
        
        results = []
        
        for post in pending_posts:
            result = asyncio.run(_publish_post(db, post))
            results.append({
                "post_id": str(post.id),
                **result,
            })
        
        return {
            "success": True,
            "processed": len(results),
            "results": results,
        }
        
    except Exception as e:
        logger.exception("Error processing scheduled posts")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
