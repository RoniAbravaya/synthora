"""
Pipeline State Manager

Manages state transitions and tracking for video generation pipeline.
Handles:
- Step status tracking
- Progress updates
- State persistence
- Resume capability
- Cleanup on failure
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session

from app.models.video import Video, GenerationStep, VideoStatus, PlanningStatus

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """
    Pipeline execution states.
    
    State transitions:
    PENDING -> QUEUED -> PROCESSING -> [step states] -> COMPLETED
                                    -> FAILED
                                    -> CANCELLED
    """
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepState(str, Enum):
    """Individual step states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStateManager:
    """
    Manages state for video generation pipeline.
    
    Responsibilities:
    - Track step status and progress
    - Update database state
    - Support resume from failed step
    - Handle cleanup on failure/cancellation
    """
    
    # Step execution order
    STEPS = [
        GenerationStep.SCRIPT,
        GenerationStep.VOICE,
        GenerationStep.MEDIA,
        GenerationStep.VIDEO_AI,
        GenerationStep.ASSEMBLY,
    ]
    
    # Progress percentage ranges for each step
    STEP_PROGRESS = {
        GenerationStep.SCRIPT: (0, 15),
        GenerationStep.VOICE: (15, 35),
        GenerationStep.MEDIA: (35, 55),
        GenerationStep.VIDEO_AI: (55, 80),
        GenerationStep.ASSEMBLY: (80, 100),
    }
    
    def __init__(self, db: Session, video: Video):
        """
        Initialize the state manager.
        
        Args:
            db: Database session
            video: Video being generated
        """
        self.db = db
        self.video = video
        self._state_cache: Dict[str, Any] = {}
    
    def initialize(self) -> None:
        """Initialize pipeline state for a new generation."""
        self.video.status = VideoStatus.PROCESSING.value
        self.video.progress = 0
        self.video.generation_started_at = datetime.utcnow()
        self.video.last_step_updated_at = datetime.utcnow()
        self.video.error_message = None
        
        # Initialize generation config if not exists
        if not self.video.generation_config:
            self.video.generation_config = {}
        
        # Initialize step states
        for step in self.STEPS:
            self.video.generation_config[step.value] = {
                "status": StepState.PENDING.value,
                "progress": 0,
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }
        
        self._commit()
        logger.info(f"Initialized pipeline state for video {self.video.id}")
    
    def start_step(self, step: GenerationStep) -> None:
        """
        Mark a step as started.
        
        Args:
            step: Step being started
        """
        now = datetime.utcnow()
        
        self.video.current_step = step.value
        self.video.last_step_updated_at = now
        
        # Update step state
        step_data = self.video.generation_config.get(step.value, {})
        step_data["status"] = StepState.PROCESSING.value
        step_data["started_at"] = now.isoformat()
        self.video.generation_config[step.value] = step_data
        
        # Update progress to step start
        progress_start, _ = self.STEP_PROGRESS[step]
        self.video.progress = progress_start
        
        self._commit()
        logger.info(f"Started step {step.value} for video {self.video.id}")
    
    def update_step_progress(self, step: GenerationStep, progress: int) -> None:
        """
        Update progress within a step.
        
        Args:
            step: Current step
            progress: Progress percentage within step (0-100)
        """
        self.video.last_step_updated_at = datetime.utcnow()
        
        step_data = self.video.generation_config.get(step.value, {})
        step_data["progress"] = progress
        self.video.generation_config[step.value] = step_data
        
        # Calculate overall progress
        progress_start, progress_end = self.STEP_PROGRESS[step]
        step_contribution = (progress_end - progress_start) * (progress / 100)
        self.video.progress = int(progress_start + step_contribution)
        
        self._commit()
    
    def complete_step(
        self,
        step: GenerationStep,
        result: Dict[str, Any],
    ) -> None:
        """
        Mark a step as completed.
        
        Args:
            step: Completed step
            result: Step result data
        """
        now = datetime.utcnow()
        
        self.video.last_step_updated_at = now
        
        step_data = self.video.generation_config.get(step.value, {})
        step_data["status"] = StepState.COMPLETED.value
        step_data["progress"] = 100
        step_data["completed_at"] = now.isoformat()
        step_data["result"] = result
        self.video.generation_config[step.value] = step_data
        
        # Update overall progress
        _, progress_end = self.STEP_PROGRESS[step]
        self.video.progress = progress_end
        
        # Store result in cache for subsequent steps
        self._state_cache[step.value] = result
        
        self._commit()
        logger.info(f"Completed step {step.value} for video {self.video.id}")
    
    def skip_step(self, step: GenerationStep, reason: str) -> None:
        """
        Mark a step as skipped.
        
        Args:
            step: Skipped step
            reason: Reason for skipping
        """
        step_data = self.video.generation_config.get(step.value, {})
        step_data["status"] = StepState.SKIPPED.value
        step_data["result"] = {"skipped": True, "reason": reason}
        self.video.generation_config[step.value] = step_data
        
        self._state_cache[step.value] = {"skipped": True}
        
        self._commit()
        logger.info(f"Skipped step {step.value} for video {self.video.id}: {reason}")
    
    def fail_step(
        self,
        step: GenerationStep,
        error: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark a step and the pipeline as failed.
        
        Args:
            step: Failed step
            error: Error message
            error_details: Additional error context
        """
        now = datetime.utcnow()
        
        # Update step state
        step_data = self.video.generation_config.get(step.value, {})
        step_data["status"] = StepState.FAILED.value
        step_data["error"] = error
        step_data["error_details"] = error_details
        step_data["completed_at"] = now.isoformat()
        self.video.generation_config[step.value] = step_data
        
        # Update video state
        self.video.status = VideoStatus.FAILED.value
        self.video.error_message = f"Failed at step {step.value}: {error}"
        self.video.last_step_updated_at = now
        
        # Update planning status if this was a scheduled video
        if self.video.planning_status in [PlanningStatus.GENERATING.value, PlanningStatus.PLANNED.value]:
            self.video.planning_status = PlanningStatus.FAILED.value
        
        self._commit()
        logger.error(f"Step {step.value} failed for video {self.video.id}: {error}")
    
    def complete_pipeline(
        self,
        video_url: str,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        file_size: Optional[int] = None,
        resolution: Optional[str] = None,
        subtitle_url: Optional[str] = None,
    ) -> None:
        """
        Mark the pipeline as completed.
        
        Args:
            video_url: URL to final video
            thumbnail_url: Optional thumbnail URL
            duration: Video duration in seconds
            file_size: File size in bytes
            resolution: Video resolution string
            subtitle_url: Optional subtitle file URL
        """
        now = datetime.utcnow()
        
        # Calculate generation time
        generation_time = None
        if self.video.generation_started_at:
            generation_time = (now - self.video.generation_started_at).total_seconds()
        
        # Collect providers used
        providers_used = []
        for step in self.STEPS:
            step_data = self.video.generation_config.get(step.value, {})
            result = step_data.get("result", {})
            if isinstance(result, dict) and result.get("provider"):
                providers_used.append(result["provider"])
        
        # Update video
        self.video.status = VideoStatus.COMPLETED.value
        self.video.progress = 100
        self.video.video_url = video_url
        self.video.thumbnail_url = thumbnail_url
        self.video.duration = duration
        self.video.file_size = file_size
        self.video.resolution = resolution
        self.video.subtitle_file_url = subtitle_url
        self.video.integrations_used = providers_used
        self.video.generation_time_seconds = generation_time
        self.video.last_step_updated_at = now
        
        # Update planning status if this was a scheduled video
        if self.video.planning_status == PlanningStatus.GENERATING.value:
            self.video.planning_status = PlanningStatus.READY.value
        
        self._commit()
        logger.info(f"Pipeline completed for video {self.video.id} in {generation_time:.1f}s")
    
    def cancel_pipeline(self, reason: str = "User cancelled") -> None:
        """
        Cancel the pipeline.
        
        Args:
            reason: Cancellation reason
        """
        self.video.status = VideoStatus.CANCELLED.value
        self.video.error_message = reason
        self.video.last_step_updated_at = datetime.utcnow()
        
        if self.video.planning_status == PlanningStatus.GENERATING.value:
            self.video.planning_status = PlanningStatus.FAILED.value
        
        self._commit()
        logger.info(f"Pipeline cancelled for video {self.video.id}: {reason}")
    
    def get_step_result(self, step: GenerationStep) -> Optional[Dict[str, Any]]:
        """
        Get the result of a completed step.
        
        Used to pass data between steps (e.g., script -> voice).
        
        Args:
            step: Step to get result for
            
        Returns:
            Step result or None
        """
        # Check cache first
        if step.value in self._state_cache:
            return self._state_cache[step.value]
        
        # Load from database
        step_data = self.video.generation_config.get(step.value, {})
        result = step_data.get("result")
        
        if result:
            self._state_cache[step.value] = result
        
        return result
    
    def get_last_completed_step(self) -> Optional[GenerationStep]:
        """
        Get the last successfully completed step.
        
        Used for resuming from a failed generation.
        
        Returns:
            Last completed step or None
        """
        last_completed = None
        
        for step in self.STEPS:
            step_data = self.video.generation_config.get(step.value, {})
            if step_data.get("status") == StepState.COMPLETED.value:
                last_completed = step
            else:
                break
        
        return last_completed
    
    def get_resume_step(self) -> Optional[GenerationStep]:
        """
        Get the step to resume from after a failure.
        
        Returns:
            Step to resume from, or None to start fresh
        """
        last_completed = self.get_last_completed_step()
        
        if last_completed is None:
            return self.STEPS[0]
        
        # Return the next step after last completed
        try:
            idx = self.STEPS.index(last_completed)
            if idx + 1 < len(self.STEPS):
                return self.STEPS[idx + 1]
        except (ValueError, IndexError):
            pass
        
        return None
    
    def is_cancelled(self) -> bool:
        """Check if the pipeline has been cancelled."""
        # Refresh from database
        self.db.refresh(self.video)
        return self.video.status == VideoStatus.CANCELLED.value
    
    def is_video_deleted(self) -> bool:
        """Check if the video still exists in the database."""
        exists = self.db.query(Video).filter(Video.id == self.video.id).first()
        return exists is None
    
    def load_previous_state(self) -> None:
        """Load state from previous steps into cache for resume."""
        for step in self.STEPS:
            result = self.get_step_result(step)
            if result:
                self._state_cache[step.value] = result
    
    def _commit(self) -> None:
        """Commit changes to database."""
        try:
            self.db.commit()
            self.db.refresh(self.video)
        except Exception as e:
            logger.error(f"Failed to commit state: {e}")
            self.db.rollback()
            raise
