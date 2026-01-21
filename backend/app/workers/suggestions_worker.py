"""
Suggestions Worker

Background jobs for generating AI suggestions.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import asyncio

from sqlalchemy.orm import Session
from rq import get_current_job

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.services.suggestions import SuggestionsService
from app.services.ai_analysis.posting_time import PostingTimeAnalyzer
from app.services.ai_analysis.content import ContentAnalyzer
from app.services.ai_analysis.trends import TrendAnalyzer
from app.services.ai_analysis.predictions import PerformancePredictor
from app.services.ai_analysis.improvements import ImprovementAnalyzer

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =========================================================================
# Suggestion Generation Jobs
# =========================================================================

def generate_posting_time_suggestions_job(user_id: str) -> dict:
    """
    Generate posting time suggestions for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        # Check if user is premium (suggestions are premium-only)
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.role == UserRole.FREE:
            return {"success": False, "error": "Premium feature only"}
        
        suggestions_service = SuggestionsService(db)
        analyzer = PostingTimeAnalyzer(db)
        
        created = analyzer.generate_suggestions(user_uuid, suggestions_service)
        
        return {
            "success": True,
            "user_id": user_id,
            "suggestions_created": len(created),
            "suggestions": created,
        }
        
    except Exception as e:
        logger.exception(f"Posting time suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def generate_content_suggestions_job(user_id: str) -> dict:
    """
    Generate content suggestions for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.role == UserRole.FREE:
            return {"success": False, "error": "Premium feature only"}
        
        suggestions_service = SuggestionsService(db)
        analyzer = ContentAnalyzer(db)
        
        created = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        
        return {
            "success": True,
            "user_id": user_id,
            "suggestions_created": len(created),
            "suggestions": created,
        }
        
    except Exception as e:
        logger.exception(f"Content suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def generate_trend_suggestions_job(user_id: str) -> dict:
    """
    Generate trend-based suggestions for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.role == UserRole.FREE:
            return {"success": False, "error": "Premium feature only"}
        
        suggestions_service = SuggestionsService(db)
        analyzer = TrendAnalyzer(db)
        
        created = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        
        return {
            "success": True,
            "user_id": user_id,
            "suggestions_created": len(created),
            "suggestions": created,
        }
        
    except Exception as e:
        logger.exception(f"Trend suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def generate_improvement_suggestions_job(user_id: str) -> dict:
    """
    Generate improvement suggestions for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.role == UserRole.FREE:
            return {"success": False, "error": "Premium feature only"}
        
        suggestions_service = SuggestionsService(db)
        analyzer = ImprovementAnalyzer(db)
        
        created = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        
        return {
            "success": True,
            "user_id": user_id,
            "suggestions_created": len(created),
            "suggestions": created,
        }
        
    except Exception as e:
        logger.exception(f"Improvement suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def generate_all_suggestions_job(user_id: str) -> dict:
    """
    Generate all types of suggestions for a user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        user_uuid = UUID(user_id)
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.role == UserRole.FREE:
            return {"success": False, "error": "Premium feature only"}
        
        suggestions_service = SuggestionsService(db)
        results = {
            "posting_time": [],
            "content": [],
            "trends": [],
            "improvements": [],
        }
        
        # Posting time suggestions
        try:
            analyzer = PostingTimeAnalyzer(db)
            results["posting_time"] = analyzer.generate_suggestions(user_uuid, suggestions_service)
        except Exception as e:
            logger.error(f"Posting time suggestions failed: {e}")
        
        # Content suggestions
        try:
            analyzer = ContentAnalyzer(db)
            results["content"] = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        except Exception as e:
            logger.error(f"Content suggestions failed: {e}")
        
        # Trend suggestions
        try:
            analyzer = TrendAnalyzer(db)
            results["trends"] = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        except Exception as e:
            logger.error(f"Trend suggestions failed: {e}")
        
        # Improvement suggestions
        try:
            analyzer = ImprovementAnalyzer(db)
            results["improvements"] = _run_async(analyzer.generate_suggestions(user_uuid, suggestions_service))
        except Exception as e:
            logger.error(f"Improvement suggestions failed: {e}")
        
        total_created = sum(len(v) for v in results.values())
        
        return {
            "success": True,
            "user_id": user_id,
            "total_suggestions_created": total_created,
            "by_type": {k: len(v) for k, v in results.items()},
        }
        
    except Exception as e:
        logger.exception(f"All suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def daily_suggestions_job() -> dict:
    """
    Daily job to generate suggestions for all premium users.
    
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        # Get all premium users
        premium_users = db.query(User).filter(
            User.role.in_([UserRole.PREMIUM, UserRole.ADMIN]),
            User.is_active == True,
        ).all()
        
        results = {
            "total_users": len(premium_users),
            "processed": 0,
            "failed": 0,
        }
        
        for user in premium_users:
            try:
                result = generate_all_suggestions_job(str(user.id))
                if result.get("success"):
                    results["processed"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to generate suggestions for user {user.id}: {e}")
                results["failed"] += 1
        
        logger.info(f"Daily suggestions job completed: {results}")
        return {
            "success": True,
            **results,
        }
        
    except Exception as e:
        logger.exception(f"Daily suggestions job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def cleanup_suggestions_job() -> dict:
    """
    Cleanup expired and old dismissed suggestions.
    
    Returns:
        Dictionary with cleanup results
    """
    db = SessionLocal()
    
    try:
        suggestions_service = SuggestionsService(db)
        
        expired_count = suggestions_service.cleanup_expired_suggestions()
        dismissed_count = suggestions_service.cleanup_old_dismissed(days=30)
        
        return {
            "success": True,
            "expired_removed": expired_count,
            "dismissed_removed": dismissed_count,
        }
        
    except Exception as e:
        logger.exception(f"Suggestions cleanup job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# =========================================================================
# Queue Helpers
# =========================================================================

def queue_suggestions_generation(user_id: UUID, queue_name: str = "suggestions") -> Optional[str]:
    """
    Queue a suggestions generation job for a user.
    
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
        
        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue(queue_name, connection=redis_conn)
        
        job = queue.enqueue(
            generate_all_suggestions_job,
            str(user_id),
            job_timeout=600,  # 10 minutes
        )
        
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue suggestions generation: {e}")
        return None

