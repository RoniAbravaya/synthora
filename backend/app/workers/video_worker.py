"""
Video Generation Worker

Background worker for processing video generation jobs.
This is the main entry point for video generation in the RQ worker.
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from rq import get_current_job
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import VideoGenerationLogger
from app.services.video import VideoService
from app.services.template import TemplateService
from app.services.user_generation_settings import UserGenerationSettingsService
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
    # Create structured logger for this video
    vlog = VideoGenerationLogger(video_id, user_id)
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info(f"VIDEO GENERATION STARTED")
    logger.info(f"  Video ID: {video_id}")
    logger.info(f"  User ID: {user_id}")
    logger.info(f"  Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"  Prompt: {prompt}")
    logger.info(f"  Template: {template_id or 'None'}")
    logger.info("=" * 60)
    
    # Get RQ job for progress tracking
    rq_job = get_current_job()
    if rq_job:
        logger.info(f"RQ Job ID: {rq_job.id}")
    
    db = get_db()
    
    try:
        # Get video record
        video_service = VideoService(db)
        video = video_service.get_by_id(UUID(video_id))
        
        if not video:
            vlog.error("init", "Video not found in database")
            return {
                "success": False,
                "error": "Video not found",
            }
        
        vlog.progress("init", 5, f"Video record loaded, current status: {video.status}")
        
        # Get template configuration if specified
        template_config = {}
        if template_id:
            template_service = TemplateService(db)
            template = template_service.get_by_id(UUID(template_id))
            if template:
                template_config = template_service.get_template_config(template)
                vlog.progress("init", 10, f"Template loaded: {template.name}")
            else:
                vlog.warning(f"Template {template_id} not found, proceeding without template")
        
        # Load user generation settings for preferred providers
        settings_service = UserGenerationSettingsService(db)
        user_settings = settings_service.get_settings(UUID(user_id))
        
        # Log user preferences
        vlog.progress("init", 12, "Loading user generation settings")
        if user_settings:
            logger.info(f"User preferred providers: script={user_settings.default_script_provider}, "
                       f"voice={user_settings.default_voice_provider}, "
                       f"media={user_settings.default_media_provider}, "
                       f"video_ai={user_settings.default_video_ai_provider}, "
                       f"assembly={user_settings.default_assembly_provider}")
        
        # Build pipeline config with user preferences
        pipeline_config = PipelineConfig(
            prompt=prompt,
            template_config=template_config,
            target_duration=template_config.get("video_structure", {}).get("duration_max", 30),
            aspect_ratio=template_config.get("visual_style", {}).get("aspect_ratio", "9:16"),
            # Apply user's preferred providers from settings
            preferred_script_provider=user_settings.default_script_provider if user_settings else None,
            preferred_voice_provider=user_settings.default_voice_provider if user_settings else None,
            preferred_media_provider=user_settings.default_media_provider if user_settings else None,
            preferred_video_ai_provider=user_settings.default_video_ai_provider if user_settings else None,
            preferred_assembly_provider=user_settings.default_assembly_provider if user_settings else None,
        )
        
        # Apply overrides (from video creation request, takes precedence over user settings)
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(pipeline_config, key):
                    setattr(pipeline_config, key, value)
                    vlog.debug(f"Config override applied: {key}={value}")
        
        vlog.progress("init", 15, "Pipeline configuration ready")
        
        # Create and run pipeline
        pipeline = GenerationPipeline(db, video, pipeline_config)
        
        vlog.start("pipeline")
        
        # Run the async pipeline
        success = asyncio.run(pipeline.run())
        
        elapsed = time.time() - start_time
        
        # Update RQ job meta
        if rq_job:
            rq_job.meta["video_id"] = video_id
            rq_job.meta["completed_at"] = datetime.utcnow().isoformat()
            rq_job.meta["duration_seconds"] = elapsed
            rq_job.save_meta()
        
        if success:
            vlog.generation_complete(elapsed)
            logger.info("=" * 60)
            logger.info(f"VIDEO GENERATION COMPLETED SUCCESSFULLY")
            logger.info(f"  Video ID: {video_id}")
            logger.info(f"  Duration: {elapsed:.1f} seconds")
            logger.info("=" * 60)
            return {
                "success": True,
                "video_id": video_id,
                "status": "completed",
                "duration_seconds": elapsed,
            }
        else:
            # Refresh video to get latest error
            db.refresh(video)
            error_msg = video.error_message or "Unknown error"
            vlog.generation_failed(error_msg, video.current_step)
            logger.error("=" * 60)
            logger.error(f"VIDEO GENERATION FAILED")
            logger.error(f"  Video ID: {video_id}")
            logger.error(f"  Error: {error_msg}")
            logger.error(f"  Failed at step: {video.current_step}")
            logger.error(f"  Duration: {elapsed:.1f} seconds")
            logger.error("=" * 60)
            return {
                "success": False,
                "video_id": video_id,
                "status": "failed",
                "error": error_msg,
                "failed_step": video.current_step,
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        vlog.generation_failed(str(e))
        logger.exception(f"VIDEO GENERATION EXCEPTION: {video_id}")
        
        # Update video status
        try:
            video = video_service.get_by_id(UUID(video_id))
            if video:
                video_service.fail_video(
                    video,
                    str(e),
                    {
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                    },
                )
                logger.info(f"Video {video_id} marked as failed in database")
        except Exception as db_err:
            logger.error(f"Failed to update video status in database: {db_err}")
        
        return {
            "success": False,
            "video_id": video_id,
            "error": str(e),
            "exception_type": type(e).__name__,
        }
        
    finally:
        db.close()
        logger.info(f"Database session closed for video {video_id}")


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
