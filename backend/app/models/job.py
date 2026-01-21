"""
Job Model

Tracks background jobs for video generation, posting, analytics sync, etc.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class JobType(str, enum.Enum):
    """Types of background jobs."""
    VIDEO_GENERATION = "video_generation"
    POST_PUBLISH = "post_publish"
    ANALYTICS_SYNC = "analytics_sync"
    VIDEO_CLEANUP = "video_cleanup"
    SUGGESTION_GENERATION = "suggestion_generation"
    TOKEN_REFRESH = "token_refresh"


class JobStatus(str, enum.Enum):
    """
    Job status values.
    
    - pending: Queued but not started
    - processing: Currently running
    - completed: Successfully finished
    - failed: Job failed
    - cancelled: Job was cancelled
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base, UUIDMixin, TimestampMixin):
    """
    Job model for tracking background jobs.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user (nullable for system jobs)
        type: Type of job
        status: Current job status
        
        # Job Data
        payload: Input data for the job (JSON)
        result: Output data from the job (JSON)
        error: Error message if failed
        
        # Progress
        progress: Progress percentage (0-100)
        current_step: Current step description
        
        # Timing
        started_at: When job started processing
        completed_at: When job completed
        
        # RQ Integration
        rq_job_id: Redis Queue job ID
        
    Relationships:
        user: The user this job belongs to (optional)
    """
    
    __tablename__ = "jobs"
    
    # Foreign Key (nullable for system jobs)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Foreign key to user"
    )
    
    # Job Info
    type = Column(
        Enum(JobType),
        nullable=False,
        index=True,
        doc="Type of job"
    )
    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
        doc="Current job status"
    )
    
    # Job Data
    payload = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Input data for the job"
    )
    result = Column(
        JSONB,
        nullable=True,
        doc="Output data from the job"
    )
    error = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )
    error_details = Column(
        JSONB,
        nullable=True,
        doc="Detailed error information"
    )
    
    # Progress
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Progress percentage (0-100)"
    )
    current_step = Column(
        String(255),
        nullable=True,
        doc="Current step description"
    )
    
    # Timing
    started_at = Column(
        DateTime,
        nullable=True,
        doc="When job started processing"
    )
    completed_at = Column(
        DateTime,
        nullable=True,
        doc="When job completed"
    )
    
    # RQ Integration
    rq_job_id = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Redis Queue job ID"
    )
    
    # Retry Info
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    max_retries = Column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum retry attempts"
    )
    
    # Relationship
    user = relationship("User", back_populates="jobs")
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type={self.type}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if job is pending."""
        return self.status == JobStatus.PENDING
    
    @property
    def is_processing(self) -> bool:
        """Check if job is processing."""
        return self.status == JobStatus.PROCESSING
    
    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == JobStatus.FAILED
    
    @property
    def is_finished(self) -> bool:
        """Check if job is finished (completed, failed, or cancelled)."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.is_failed and self.retry_count < self.max_retries
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.utcnow()
    
    def update_progress(self, progress: int, current_step: str = None) -> None:
        """
        Update job progress.
        
        Args:
            progress: Progress percentage (0-100)
            current_step: Current step description
        """
        self.progress = min(100, max(0, progress))
        if current_step:
            self.current_step = current_step
    
    def complete(self, result: Dict[str, Any] = None) -> None:
        """
        Mark job as completed.
        
        Args:
            result: Job result data
        """
        self.status = JobStatus.COMPLETED
        self.progress = 100
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result
    
    def fail(self, error_message: str, error_details: Dict[str, Any] = None) -> None:
        """
        Mark job as failed.
        
        Args:
            error_message: Human-readable error message
            error_details: Additional error details
        """
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error_message
        self.error_details = error_details
    
    def cancel(self) -> None:
        """Cancel the job."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def retry(self) -> bool:
        """
        Prepare job for retry.
        
        Returns:
            True if job can be retried, False otherwise
        """
        if not self.can_retry:
            return False
        
        self.status = JobStatus.PENDING
        self.retry_count += 1
        self.error = None
        self.error_details = None
        self.progress = 0
        self.current_step = None
        self.started_at = None
        self.completed_at = None
        
        return True

