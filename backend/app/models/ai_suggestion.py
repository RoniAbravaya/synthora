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


class SuggestionType(str, enum.Enum):
    """
    Types of AI suggestions.
    
    - posting_time: Optimal posting time recommendations
    - content: Content topic/style recommendations
    - template: Template usage recommendations
    - trend: Trending topic alerts
    - prediction: Performance predictions
    - improvement: Tips for improving content
    """
    POSTING_TIME = "posting_time"
    CONTENT = "content"
    TEMPLATE = "template"
    TREND = "trend"
    PREDICTION = "prediction"
    IMPROVEMENT = "improvement"


class AISuggestion(Base, UUIDMixin, TimestampMixin):
    """
    AI Suggestion model for storing AI-generated recommendations.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        type: Type of suggestion
        title: Short title for the suggestion
        suggestion: Detailed suggestion data (JSON)
        confidence_score: AI confidence in this suggestion (0-1)
        is_read: Whether user has read this suggestion
        is_dismissed: Whether user has dismissed this suggestion
        expires_at: When this suggestion is no longer relevant
        
    Relationships:
        user: The user this suggestion is for
    """
    
    __tablename__ = "ai_suggestions"
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Suggestion Info
    type = Column(
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
    suggestion = Column(
        JSONB,
        nullable=False,
        doc="Detailed suggestion data"
    )
    
    # Confidence
    confidence_score = Column(
        Float,
        default=0.5,
        nullable=False,
        doc="AI confidence in this suggestion (0-1)"
    )
    
    # Status
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
    
    # Expiry
    expires_at = Column(
        DateTime,
        nullable=True,
        doc="When this suggestion is no longer relevant"
    )
    
    # Relationship
    user = relationship("User", back_populates="suggestions")
    
    def __repr__(self) -> str:
        return f"<AISuggestion(id={self.id}, type={self.type}, title={self.title})>"
    
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
    
    def dismiss(self) -> None:
        """Dismiss the suggestion."""
        self.is_dismissed = True
    
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
            type=SuggestionType.POSTING_TIME,
            title="Optimal Posting Times",
            suggestion={
                "recommended_times": recommended_times,
                "reasoning": reasoning,
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
            type=SuggestionType.CONTENT,
            title=f"Content Idea: {topic}",
            suggestion={
                "topic": topic,
                "reasoning": reasoning,
                "related_trends": related_trends or [],
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
        return AISuggestion(
            user_id=user_id,
            type=SuggestionType.TREND,
            title=f"Trending: {trend_name}",
            suggestion={
                "trend_name": trend_name,
                "description": description,
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
            type=SuggestionType.IMPROVEMENT,
            title=f"Improve Your {area.title()}",
            suggestion={
                "area": area,
                "tip": tip,
                "examples": examples or [],
                "based_on": "content_analysis"
            },
            confidence_score=confidence
        )

