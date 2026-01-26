"""
Video Generation Worker

Background worker for processing video generation jobs.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from rq import get_current_job
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.video import VideoService
from app.services.template import TemplateService
from app.services.generation.pipeline import GenerationPipeline, PipelineConfig
from app.models.video import Video, VideoStatus
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get a database session for the worker."""
    return SessionLocal()


def process_video_generation(
    video_id: str,
    user_id: str,
    prompt: str,
    template_id: Optional[str] = None,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a video generation job.
    
    This is the main entry point for video generation workers.
    
    Args:
        video_id: UUID of the video to generate
        user_id: UUID of the user
        prompt: Video topic/prompt
        template_id: Optional template UUID
        config_overrides: Optional configuration overrides
        
    Returns:
        Dictionary with job result
    """
    logger.info(f"Starting video generation job for video {video_id}")
    
    # Get RQ job for progress tracking
    rq_job = get_current_job()
    
    db = get_db()
    
    try:
        # Get video record
        video_service = VideoService(db)
        video = video_service.get_by_id(UUID(video_id))
        
        if not video:
            logger.error(f"Video not found: {video_id}")
            return {
                "success": False,
                "error": "Video not found",
            }
        
        # Get template configuration if specified
        template_config = {}
        if template_id:
            template_service = TemplateService(db)
            template = template_service.get_by_id(UUID(template_id))
            if template:
                template_config = template_service.get_template_config(template)
        
        # Build pipeline config
        pipeline_config = PipelineConfig(
            prompt=prompt,
            template_config=template_config,
            target_duration=template_config.get("video_structure", {}).get("duration_max", 30),
            aspect_ratio=template_config.get("visual_style", {}).get("aspect_ratio", "9:16"),
        )
        
        # Apply overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(pipeline_config, key):
                    setattr(pipeline_config, key, value)
        
        # Create and run pipeline
        pipeline = GenerationPipeline(db, video, pipeline_config)
        
        # Run the async pipeline
        success = asyncio.run(pipeline.run())
        
        # Update RQ job meta
        if rq_job:
            rq_job.meta["video_id"] = video_id
            rq_job.meta["completed_at"] = datetime.utcnow().isoformat()
            rq_job.save_meta()
        
        if success:
            logger.info(f"Video generation completed: {video_id}")
            return {
                "success": True,
                "video_id": video_id,
                "status": "completed",
            }
        else:
            logger.error(f"Video generation failed: {video_id}")
            return {
                "success": False,
                "video_id": video_id,
                "status": "failed",
                "error": video.error_message,
            }
            
    except Exception as e:
        logger.exception(f"Video generation error: {video_id}")
        
        # Update video status
        try:
            video = video_service.get_by_id(UUID(video_id))
            if video:
                video_service.fail_video(
                    video,
                    str(e),
                    {"exception_type": type(e).__name__},
                )
        except Exception:
            pass
        
        return {
            "success": False,
            "video_id": video_id,
            "error": str(e),
        }
        
    finally:
        db.close()


def retry_video_generation(
    video_id: str,
    swap_integration: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Retry a failed video generation.
    
    Can optionally swap integrations for failed steps.
    
    Args:
        video_id: UUID of the video to retry
        swap_integration: Optional dict mapping step -> new provider
        
    Returns:
        Dictionary with job result
    """
    logger.info(f"Retrying video generation for video {video_id}")
    
    db = get_db()
    
    try:
        video_service = VideoService(db)
        video = video_service.get_by_id(UUID(video_id))
        
        if not video:
            return {
                "success": False,
                "error": "Video not found",
            }
        
        # Use string comparisons
        if video.status not in ["failed", "processing"]:
            return {
                "success": False,
                "error": f"Cannot retry video in status: {video.status}",
            }
        
        # Reset video status to pending (use string)
        video_service.update_status(video, "pending", progress=0)
        
        # Get the original prompt and template
        prompt = video.prompt
        template_id = str(video.template_id) if video.template_id else None
        
        # Build config overrides with swapped integrations
        config_overrides = {}
        if swap_integration:
            for step, provider in swap_integration.items():
                config_key = f"preferred_{step}_provider"
                config_overrides[config_key] = provider
        
        # Run generation
        return process_video_generation(
            video_id=video_id,
            user_id=str(video.user_id),
            prompt=prompt,
            template_id=template_id,
            config_overrides=config_overrides,
        )
        
    except Exception as e:
        logger.exception(f"Retry error for video {video_id}")
        return {
            "success": False,
            "error": str(e),
        }
        
    finally:
        db.close()


def update_job_progress(job_id: str, progress: int, message: str) -> None:
    """
    Update job progress in the database.
    
    Args:
        job_id: Job UUID
        progress: Progress percentage (0-100)
        message: Progress message
    """
    db = get_db()
    
    try:
        job = db.query(Job).filter(Job.id == UUID(job_id)).first()
        if job:
            job.progress = progress
            job.result = {"message": message}
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")
    finally:
        db.close()
