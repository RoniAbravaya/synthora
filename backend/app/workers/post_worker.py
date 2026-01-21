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
        
        # Check if post is still scheduled
        if post.status != PostStatus.SCHEDULED:
            logger.warning(f"Post {post_id} is not scheduled (status: {post.status.value})")
            return {"success": False, "error": f"Post status is {post.status.value}"}
        
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
    logger.info(f"Publishing post now: {post_id}")
    
    db = get_db()
    
    try:
        post_service = PostService(db)
        post = post_service.get_by_id(UUID(post_id))
        
        if not post:
            return {"success": False, "error": "Post not found"}
        
        if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
            return {"success": False, "error": f"Cannot publish post in status: {post.status.value}"}
        
        result = asyncio.run(_publish_post(db, post))
        
        return result
        
    except Exception as e:
        logger.exception(f"Error publishing post {post_id}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


async def _publish_post(db: Session, post: Post) -> Dict[str, Any]:
    """
    Internal function to publish a post to all platforms.
    
    Args:
        db: Database session
        post: Post to publish
        
    Returns:
        Dictionary with results
    """
    post_service = PostService(db)
    oauth_service = SocialOAuthService(db)
    
    # Mark post as publishing
    post_service.start_publishing(post)
    
    # Get video
    video = db.query(Video).filter(Video.id == post.video_id).first()
    if not video:
        post_service.update_platform_status(
            post, 
            SocialPlatform(post.platforms[0]) if post.platforms else SocialPlatform.YOUTUBE,
            "failed",
            error="Video not found"
        )
        return {"success": False, "error": "Video not found"}
    
    results = {}
    
    # Publish to each platform
    for platform_str in post.platforms:
        platform = SocialPlatform(platform_str)
        
        # Update platform status to publishing
        post_service.update_platform_status(post, platform, "publishing")
        
        # Get social account for this platform
        accounts = oauth_service.get_user_accounts(post.user_id, platform)
        
        if not accounts:
            post_service.update_platform_status(
                post, platform, "failed",
                error=f"No {platform.value} account connected"
            )
            results[platform_str] = {
                "success": False,
                "error": f"No {platform.value} account connected"
            }
            continue
        
        account = accounts[0]  # Use first account
        
        # Get access token
        access_token = oauth_service.get_access_token(account)
        
        if not access_token:
            post_service.update_platform_status(
                post, platform, "failed",
                error="Failed to get access token"
            )
            results[platform_str] = {
                "success": False,
                "error": "Failed to get access token"
            }
            continue
        
        # Get platform-specific overrides
        platform_overrides = (post.platform_overrides or {}).get(platform_str, {})
        
        # Create publish request
        request = PublishRequest(
            video_path=video.video_url or "",  # Local path or URL
            video_url=video.video_url,  # Public URL for Instagram
            title=post.title or video.title or "Untitled",
            description=post.description or "",
            hashtags=post.hashtags or [],
            access_token=access_token,
            platform_overrides=platform_overrides,
        )
        
        # Get publisher and publish
        try:
            publisher = get_publisher(platform)
            result = await publisher.publish(request)
            
            if result.success:
                post_service.update_platform_status(
                    post, platform, "published",
                    post_id=result.post_id,
                    post_url=result.post_url,
                )
            else:
                post_service.update_platform_status(
                    post, platform, "failed",
                    error=result.error,
                )
            
            results[platform_str] = result.to_dict()
            
        except Exception as e:
            logger.exception(f"Error publishing to {platform_str}")
            post_service.update_platform_status(
                post, platform, "failed",
                error=str(e),
            )
            results[platform_str] = {
                "success": False,
                "error": str(e)
            }
    
    # Determine overall success
    successes = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    return {
        "success": successes > 0,
        "post_id": str(post.id),
        "platforms_succeeded": successes,
        "platforms_total": total,
        "results": results,
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

