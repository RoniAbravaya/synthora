"""
AI Suggestions Service

Business logic for generating, storing, and managing AI-powered suggestions.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.ai_suggestion import AISuggestion, SuggestionType, SuggestionPriority
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class SuggestionsService:
    """
    Service class for AI suggestions management.
    
    Handles:
    - Creating and storing suggestions
    - Retrieving user suggestions
    - Managing suggestion lifecycle (read, dismiss, act)
    - Generating various suggestion types
    """
    
    def __init__(self, db: Session):
        """
        Initialize the suggestions service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_user_suggestions(
        self,
        user_id: UUID,
        suggestion_type: Optional[SuggestionType] = None,
        include_read: bool = False,
        include_dismissed: bool = False,
        limit: int = 20,
    ) -> List[AISuggestion]:
        """
        Get suggestions for a user.
        
        Args:
            user_id: User UUID
            suggestion_type: Optional filter by type
            include_read: Include already read suggestions
            include_dismissed: Include dismissed suggestions
            limit: Maximum number of suggestions
            
        Returns:
            List of AISuggestion records
        """
        query = self.db.query(AISuggestion).filter(
            AISuggestion.user_id == user_id
        )
        
        if suggestion_type:
            query = query.filter(AISuggestion.suggestion_type == suggestion_type)
        
        if not include_read:
            query = query.filter(AISuggestion.is_read == False)
        
        if not include_dismissed:
            query = query.filter(AISuggestion.is_dismissed == False)
        
        # Filter out expired suggestions
        query = query.filter(
            or_(
                AISuggestion.expires_at.is_(None),
                AISuggestion.expires_at > datetime.utcnow(),
            )
        )
        
        # Order by priority and creation date
        query = query.order_by(
            AISuggestion.priority.desc(),
            AISuggestion.created_at.desc(),
        )
        
        return query.limit(limit).all()
    
    def get_suggestion_by_id(
        self,
        suggestion_id: UUID,
        user_id: UUID,
    ) -> Optional[AISuggestion]:
        """Get a specific suggestion by ID."""
        return self.db.query(AISuggestion).filter(
            and_(
                AISuggestion.id == suggestion_id,
                AISuggestion.user_id == user_id,
            )
        ).first()
    
    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread suggestions."""
        return self.db.query(AISuggestion).filter(
            and_(
                AISuggestion.user_id == user_id,
                AISuggestion.is_read == False,
                AISuggestion.is_dismissed == False,
                or_(
                    AISuggestion.expires_at.is_(None),
                    AISuggestion.expires_at > datetime.utcnow(),
                ),
            )
        ).count()
    
    # =========================================================================
    # Create Methods
    # =========================================================================
    
    def create_suggestion(
        self,
        user_id: UUID,
        suggestion_type: SuggestionType,
        title: str,
        description: str,
        priority: SuggestionPriority = SuggestionPriority.MEDIUM,
        action_type: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        related_video_id: Optional[UUID] = None,
        related_post_id: Optional[UUID] = None,
        related_template_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AISuggestion:
        """
        Create a new suggestion.
        
        Args:
            user_id: User UUID
            suggestion_type: Type of suggestion
            title: Short title
            description: Detailed description
            priority: Suggestion priority
            action_type: Type of action (e.g., "schedule_post", "use_template")
            action_data: Data needed to perform the action
            related_video_id: Related video if applicable
            related_post_id: Related post if applicable
            related_template_id: Related template if applicable
            expires_at: When the suggestion expires
            metadata: Additional metadata
            
        Returns:
            Created AISuggestion instance
        """
        suggestion = AISuggestion(
            user_id=user_id,
            suggestion_type=suggestion_type,
            title=title,
            description=description,
            priority=priority,
            action_type=action_type,
            action_data=action_data or {},
            related_video_id=related_video_id,
            related_post_id=related_post_id,
            related_template_id=related_template_id,
            expires_at=expires_at,
            extra_data=metadata or {},
        )
        
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        
        logger.info(f"Created {suggestion_type.value} suggestion for user {user_id}")
        return suggestion
    
    def create_posting_time_suggestion(
        self,
        user_id: UUID,
        platform: str,
        recommended_day: str,
        recommended_hour: int,
        engagement_boost: float,
        based_on_posts: int,
    ) -> AISuggestion:
        """
        Create a posting time suggestion.
        
        Args:
            user_id: User UUID
            platform: Target platform
            recommended_day: Day of week
            recommended_hour: Hour (0-23)
            engagement_boost: Expected engagement improvement %
            based_on_posts: Number of posts analyzed
            
        Returns:
            Created suggestion
        """
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.OPTIMAL_TIME,
            title=f"Best time to post on {platform}",
            description=f"Based on your last {based_on_posts} posts, posting on {recommended_day} at {recommended_hour}:00 could increase engagement by {engagement_boost:.1f}%.",
            priority=SuggestionPriority.MEDIUM,
            action_type="schedule_post",
            action_data={
                "platform": platform,
                "day": recommended_day,
                "hour": recommended_hour,
                "engagement_boost": engagement_boost,
            },
            metadata={
                "based_on_posts": based_on_posts,
                "analysis_date": datetime.utcnow().isoformat(),
            },
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    
    def create_content_suggestion(
        self,
        user_id: UUID,
        content_type: str,
        recommendation: str,
        reasoning: str,
        examples: Optional[List[str]] = None,
    ) -> AISuggestion:
        """
        Create a content recommendation suggestion.
        
        Args:
            user_id: User UUID
            content_type: Type of content (topic, style, format)
            recommendation: The actual recommendation
            reasoning: Why this is recommended
            examples: Example content ideas
            
        Returns:
            Created suggestion
        """
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.CONTENT,
            title=f"Content idea: {content_type}",
            description=f"{recommendation}\n\n{reasoning}",
            priority=SuggestionPriority.MEDIUM,
            action_type="create_video",
            action_data={
                "content_type": content_type,
                "examples": examples or [],
            },
            expires_at=datetime.utcnow() + timedelta(days=14),
        )
    
    def create_template_suggestion(
        self,
        user_id: UUID,
        template_id: UUID,
        template_name: str,
        reason: str,
        expected_performance: str,
    ) -> AISuggestion:
        """
        Create a template suggestion.
        
        Args:
            user_id: User UUID
            template_id: Suggested template ID
            template_name: Template name
            reason: Why this template is suggested
            expected_performance: Expected performance description
            
        Returns:
            Created suggestion
        """
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.TEMPLATE,
            title=f"Try the '{template_name}' template",
            description=f"{reason}\n\nExpected performance: {expected_performance}",
            priority=SuggestionPriority.LOW,
            action_type="use_template",
            action_data={
                "template_id": str(template_id),
                "template_name": template_name,
            },
            related_template_id=template_id,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    
    def create_trend_alert(
        self,
        user_id: UUID,
        trend_topic: str,
        trend_description: str,
        relevance_score: float,
        suggested_action: str,
    ) -> AISuggestion:
        """
        Create a trend alert suggestion.
        
        Args:
            user_id: User UUID
            trend_topic: Trending topic
            trend_description: Description of the trend
            relevance_score: How relevant to user (0-1)
            suggested_action: What to do about it
            
        Returns:
            Created suggestion
        """
        priority = SuggestionPriority.HIGH if relevance_score > 0.8 else SuggestionPriority.MEDIUM
        
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.TREND,
            title=f"🔥 Trending: {trend_topic}",
            description=f"{trend_description}\n\nSuggested action: {suggested_action}",
            priority=priority,
            action_type="create_video",
            action_data={
                "trend_topic": trend_topic,
                "relevance_score": relevance_score,
            },
            metadata={
                "relevance_score": relevance_score,
            },
            expires_at=datetime.utcnow() + timedelta(days=3),  # Trends expire quickly
        )
    
    def create_performance_prediction(
        self,
        user_id: UUID,
        video_id: UUID,
        predicted_views: int,
        predicted_engagement: float,
        confidence: float,
        factors: List[str],
    ) -> AISuggestion:
        """
        Create a performance prediction suggestion.
        
        Args:
            user_id: User UUID
            video_id: Video UUID
            predicted_views: Predicted view count
            predicted_engagement: Predicted engagement rate
            confidence: Prediction confidence (0-1)
            factors: Factors influencing the prediction
            
        Returns:
            Created suggestion
        """
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.PREDICTION,
            title="Performance prediction for your video",
            description=f"Based on similar content, we predict ~{predicted_views:,} views with {predicted_engagement:.1f}% engagement.\n\nKey factors: {', '.join(factors)}",
            priority=SuggestionPriority.LOW,
            action_data={
                "predicted_views": predicted_views,
                "predicted_engagement": predicted_engagement,
                "confidence": confidence,
                "factors": factors,
            },
            related_video_id=video_id,
            metadata={
                "confidence": confidence,
            },
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    
    def create_improvement_tip(
        self,
        user_id: UUID,
        tip_category: str,
        tip_title: str,
        tip_description: str,
        impact_level: str,
        related_post_id: Optional[UUID] = None,
    ) -> AISuggestion:
        """
        Create an improvement tip suggestion.
        
        Args:
            user_id: User UUID
            tip_category: Category (hook, thumbnail, hashtags, etc.)
            tip_title: Short title
            tip_description: Detailed tip
            impact_level: Expected impact (high, medium, low)
            related_post_id: Related post if applicable
            
        Returns:
            Created suggestion
        """
        priority_map = {
            "high": SuggestionPriority.HIGH,
            "medium": SuggestionPriority.MEDIUM,
            "low": SuggestionPriority.LOW,
        }
        
        return self.create_suggestion(
            user_id=user_id,
            suggestion_type=SuggestionType.IMPROVEMENT,
            title=tip_title,
            description=tip_description,
            priority=priority_map.get(impact_level, SuggestionPriority.MEDIUM),
            action_type="improve_content",
            action_data={
                "category": tip_category,
                "impact_level": impact_level,
            },
            related_post_id=related_post_id,
            expires_at=datetime.utcnow() + timedelta(days=14),
        )
    
    # =========================================================================
    # Update Methods
    # =========================================================================
    
    def mark_as_read(self, suggestion_id: UUID, user_id: UUID) -> Optional[AISuggestion]:
        """Mark a suggestion as read."""
        suggestion = self.get_suggestion_by_id(suggestion_id, user_id)
        if suggestion:
            suggestion.is_read = True
            suggestion.read_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(suggestion)
        return suggestion
    
    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all suggestions as read for a user."""
        count = self.db.query(AISuggestion).filter(
            and_(
                AISuggestion.user_id == user_id,
                AISuggestion.is_read == False,
            )
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow(),
        })
        self.db.commit()
        return count
    
    def dismiss_suggestion(self, suggestion_id: UUID, user_id: UUID) -> Optional[AISuggestion]:
        """Dismiss a suggestion."""
        suggestion = self.get_suggestion_by_id(suggestion_id, user_id)
        if suggestion:
            suggestion.is_dismissed = True
            suggestion.dismissed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(suggestion)
        return suggestion
    
    def mark_as_acted(self, suggestion_id: UUID, user_id: UUID) -> Optional[AISuggestion]:
        """Mark that the user acted on a suggestion."""
        suggestion = self.get_suggestion_by_id(suggestion_id, user_id)
        if suggestion:
            suggestion.is_acted = True
            suggestion.acted_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(suggestion)
        return suggestion
    
    # =========================================================================
    # Cleanup Methods
    # =========================================================================
    
    def cleanup_expired_suggestions(self) -> int:
        """Remove expired suggestions."""
        count = self.db.query(AISuggestion).filter(
            and_(
                AISuggestion.expires_at.isnot(None),
                AISuggestion.expires_at < datetime.utcnow(),
            )
        ).delete()
        self.db.commit()
        return count
    
    def cleanup_old_dismissed(self, days: int = 30) -> int:
        """Remove old dismissed suggestions."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(AISuggestion).filter(
            and_(
                AISuggestion.is_dismissed == True,
                AISuggestion.dismissed_at < cutoff,
            )
        ).delete()
        self.db.commit()
        return count


def get_suggestions_service(db: Session) -> SuggestionsService:
    """Factory function to create a SuggestionsService instance."""
    return SuggestionsService(db)

