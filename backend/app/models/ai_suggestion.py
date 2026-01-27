"""
AI Suggestion Model

Stores AI-generated recommendations for improving content (Premium feature).
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video
    from app.models.post import Post
    from app.models.template import Template


class SuggestionType(str, enum.Enum):
    """
    Types of AI suggestions.
    
    - optimal_time: Optimal posting time recommendations
    - content: Content topic/style recommendations
    - template: Template usage recommendations
    - trend: Trending topic alerts
    - prediction: Performance predictions
    - improvement: Tips for improving content
    """
    OPTIMAL_TIME = "optimal_time"
    CONTENT = "content"
    TEMPLATE = "template"
    TREND = "trend"
    PREDICTION = "prediction"
    IMPROVEMENT = "improvement"
    # Keep old values for backwards compatibility
    POSTING_TIME = "posting_time"


class SuggestionPriority(str, enum.Enum):
    """
    Priority levels for AI suggestions.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AISuggestion(Base, UUIDMixin, TimestampMixin):
    """
    AI Suggestion model for storing AI-generated recommendations.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        suggestion_type: Type of suggestion
        title: Short title for the suggestion
        description: Detailed description of the suggestion
        priority: Priority level (high/medium/low)
        action_type: Type of action user can take
        action_data: Data needed to perform the action (JSON)
        is_read: Whether user has read this suggestion
        is_dismissed: Whether user has dismissed this suggestion
        is_acted: Whether user has acted on this suggestion
        read_at: When the suggestion was read
        dismissed_at: When the suggestion was dismissed
        acted_at: When the user acted on this suggestion
        expires_at: When this suggestion is no longer relevant
        related_video_id: Related video if applicable
        related_post_id: Related post if applicable
        related_template_id: Related template if applicable
        metadata: Additional metadata (JSON)
        
    Relationships:
        user: The user this suggestion is for
        related_video: Related video
        related_post: Related post
        related_template: Related template
    """
    
    __tablename__ = "ai_suggestions"
    
    # Foreign Key - User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Suggestion Info
    suggestion_type = Column(
        Enum(SuggestionType),
        nullable=False,
        index=True,
        doc="Type of suggestion"
    )
    title = Column(
        String(255),
        nullable=False,
        doc="Short title for the suggestion"
    )
    description = Column(
        Text,
        nullable=True,
        doc="Detailed description of the suggestion"
    )
    priority = Column(
        Enum(SuggestionPriority),
        default=SuggestionPriority.MEDIUM,
        nullable=False,
        index=True,
        doc="Priority level"
    )
    
    # Action info
    action_type = Column(
        String(50),
        nullable=True,
        doc="Type of action user can take"
    )
    action_data = Column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Data needed to perform the action"
    )
    
    # Status flags
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether user has read this suggestion"
    )
    is_dismissed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user has dismissed this suggestion"
    )
    is_acted = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user has acted on this suggestion"
    )
    
    # Status timestamps
    read_at = Column(
        DateTime,
        nullable=True,
        doc="When the suggestion was read"
    )
    dismissed_at = Column(
        DateTime,
        nullable=True,
        doc="When the suggestion was dismissed"
    )
    acted_at = Column(
        DateTime,
        nullable=True,
        doc="When the user acted on this suggestion"
    )
    expires_at = Column(
        DateTime,
        nullable=True,
        doc="When this suggestion is no longer relevant"
    )
    
    # Related entities
    related_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related video if applicable"
    )
    related_post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related post if applicable"
    )
    related_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related template if applicable"
    )
    
    # Additional metadata
    extra_data = Column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Additional metadata"
    )
    
    # Legacy field for backwards compatibility (maps to description)
    suggestion = Column(
        JSONB,
        nullable=True,
        doc="Legacy: Detailed suggestion data (use description instead)"
    )
    
    # Legacy field for backwards compatibility
    confidence_score = Column(
        Float,
        default=0.5,
        nullable=True,
        doc="Legacy: AI confidence in this suggestion (0-1)"
    )
    
    # Relationships
    user = relationship("User", back_populates="suggestions")
    related_video = relationship("Video", foreign_keys=[related_video_id])
    related_post = relationship("Post", foreign_keys=[related_post_id])
    related_template = relationship("Template", foreign_keys=[related_template_id])
    
    def __repr__(self) -> str:
        return f"<AISuggestion(id={self.id}, type={self.suggestion_type}, title={self.title})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if suggestion is active (not dismissed, not expired)."""
        return not self.is_dismissed and not self.is_expired
    
    def mark_read(self) -> None:
        """Mark suggestion as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def dismiss(self) -> None:
        """Dismiss the suggestion."""
        self.is_dismissed = True
        self.dismissed_at = datetime.utcnow()
    
    def mark_acted(self) -> None:
        """Mark that user acted on this suggestion."""
        self.is_acted = True
        self.acted_at = datetime.utcnow()
    
    @staticmethod
    def create_posting_time_suggestion(
        user_id: str,
        recommended_times: list,
        reasoning: str,
        confidence: float = 0.7
    ) -> "AISuggestion":
        """
        Factory method to create a posting time suggestion.
        
        Args:
            user_id: User ID
            recommended_times: List of recommended posting times
            reasoning: Explanation for the recommendation
            confidence: Confidence score
            
        Returns:
            New AISuggestion instance
        """
        return AISuggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.OPTIMAL_TIME,
            title="Optimal Posting Times",
            description=reasoning,
            priority=SuggestionPriority.MEDIUM,
            action_type="schedule_post",
            action_data={
                "recommended_times": recommended_times,
            },
            extra_data={
                "based_on": "historical_performance"
            },
            confidence_score=confidence
        )
    
    @staticmethod
    def create_content_suggestion(
        user_id: str,
        topic: str,
        reasoning: str,
        related_trends: list = None,
        confidence: float = 0.6
    ) -> "AISuggestion":
        """
        Factory method to create a content suggestion.
        
        Args:
            user_id: User ID
            topic: Suggested content topic
            reasoning: Why this topic is recommended
            related_trends: Related trending topics
            confidence: Confidence score
            
        Returns:
            New AISuggestion instance
        """
        return AISuggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.CONTENT,
            title=f"Content Idea: {topic}",
            description=reasoning,
            priority=SuggestionPriority.MEDIUM,
            action_type="create_video",
            action_data={
                "topic": topic,
                "related_trends": related_trends or [],
            },
            extra_data={
                "based_on": "performance_analysis"
            },
            confidence_score=confidence
        )
    
    @staticmethod
    def create_trend_alert(
        user_id: str,
        trend_name: str,
        description: str,
        relevance_score: float,
        expires_at: datetime = None
    ) -> "AISuggestion":
        """
        Factory method to create a trend alert.
        
        Args:
            user_id: User ID
            trend_name: Name of the trend
            description: Description of the trend
            relevance_score: How relevant this trend is to user's content
            expires_at: When the trend expires
            
        Returns:
            New AISuggestion instance
        """
        priority = SuggestionPriority.HIGH if relevance_score > 0.8 else SuggestionPriority.MEDIUM
        
        return AISuggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.TREND,
            title=f"Trending: {trend_name}",
            description=description,
            priority=priority,
            action_type="create_video",
            action_data={
                "trend_name": trend_name,
            },
            extra_data={
                "relevance_score": relevance_score
            },
            confidence_score=relevance_score,
            expires_at=expires_at
        )
    
    @staticmethod
    def create_improvement_tip(
        user_id: str,
        area: str,
        tip: str,
        examples: list = None,
        confidence: float = 0.8
    ) -> "AISuggestion":
        """
        Factory method to create an improvement tip.
        
        Args:
            user_id: User ID
            area: Area to improve (e.g., "hook", "retention")
            tip: The improvement tip
            examples: Example implementations
            confidence: Confidence score
            
        Returns:
            New AISuggestion instance
        """
        return AISuggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.IMPROVEMENT,
            title=f"Improve Your {area.title()}",
            description=tip,
            priority=SuggestionPriority.MEDIUM,
            action_type="improve_content",
            action_data={
                "area": area,
                "examples": examples or [],
            },
            extra_data={
                "based_on": "content_analysis"
            },
            confidence_score=confidence
        )

