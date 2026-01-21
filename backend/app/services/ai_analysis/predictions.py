"""
Performance Predictor

Predicts video performance based on historical data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.video import Video
from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.models.template import Template
from app.services.suggestions import SuggestionsService
from app.models.ai_suggestion import SuggestionType

logger = logging.getLogger(__name__)


class PerformancePredictor:
    """
    Predicts video performance based on historical data and content features.
    
    Uses:
    - Historical performance of similar content
    - Template performance averages
    - Posting time patterns
    - Platform-specific benchmarks
    """
    
    def __init__(self, db: Session):
        """
        Initialize the predictor.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def predict_video_performance(
        self,
        user_id: UUID,
        video_id: UUID,
        target_platforms: List[str],
    ) -> Dict[str, Any]:
        """
        Predict performance for a video before posting.
        
        Args:
            user_id: User UUID
            video_id: Video UUID
            target_platforms: Platforms where video will be posted
            
        Returns:
            Prediction results
        """
        video = self.db.query(Video).filter(
            and_(
                Video.id == video_id,
                Video.user_id == user_id,
            )
        ).first()
        
        if not video:
            return {"success": False, "error": "Video not found"}
        
        # Get user's historical performance
        historical = self._get_historical_performance(user_id)
        
        if not historical["has_data"]:
            return {
                "success": False,
                "error": "Not enough historical data for prediction",
            }
        
        # Get template performance if applicable
        template_factor = 1.0
        if video.template_id:
            template_factor = self._get_template_performance_factor(video.template_id)
        
        # Calculate predictions
        predictions = {}
        factors = []
        
        for platform in target_platforms:
            platform_data = historical.get("by_platform", {}).get(platform, {})
            
            if platform_data:
                avg_views = platform_data.get("avg_views", historical["avg_views"])
                avg_engagement = platform_data.get("avg_engagement", historical["avg_engagement"])
            else:
                avg_views = historical["avg_views"]
                avg_engagement = historical["avg_engagement"]
            
            # Apply template factor
            predicted_views = int(avg_views * template_factor)
            predicted_engagement = avg_engagement * template_factor
            
            predictions[platform] = {
                "predicted_views": predicted_views,
                "predicted_engagement_rate": round(predicted_engagement, 2),
                "view_range": {
                    "low": int(predicted_views * 0.5),
                    "high": int(predicted_views * 1.5),
                },
            }
        
        # Determine factors
        if template_factor > 1.1:
            factors.append("Template historically performs above average")
        elif template_factor < 0.9:
            factors.append("Template historically performs below average")
        
        if historical["trend"] == "improving":
            factors.append("Your recent content shows improving performance")
        elif historical["trend"] == "declining":
            factors.append("Recent performance has been declining")
        
        if not factors:
            factors.append("Based on your average historical performance")
        
        # Calculate overall prediction
        total_predicted_views = sum(p["predicted_views"] for p in predictions.values())
        avg_predicted_engagement = statistics.mean(
            p["predicted_engagement_rate"] for p in predictions.values()
        ) if predictions else 0
        
        # Calculate confidence based on data quality
        confidence = min(0.9, 0.3 + (historical["post_count"] * 0.02))
        
        return {
            "success": True,
            "video_id": str(video_id),
            "predictions": predictions,
            "total_predicted_views": total_predicted_views,
            "avg_predicted_engagement": round(avg_predicted_engagement, 2),
            "confidence": round(confidence, 2),
            "factors": factors,
            "based_on_posts": historical["post_count"],
        }
    
    def _get_historical_performance(self, user_id: UUID) -> Dict[str, Any]:
        """Get user's historical performance data."""
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == PostStatus.PUBLISHED,
                Post.published_at >= cutoff,
            )
        ).all()
        
        if len(posts) < 3:
            return {"has_data": False, "post_count": len(posts)}
        
        # Collect performance data
        views_list = []
        engagement_list = []
        by_platform = {}
        recent_performance = []
        
        for post in posts:
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).all()
            
            if not analytics:
                continue
            
            total_views = sum(a.views for a in analytics)
            total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
            
            engagement_rate = 0.0
            if total_views > 0:
                engagement_rate = (total_engagement / total_views) * 100
            
            views_list.append(total_views)
            engagement_list.append(engagement_rate)
            
            # Track by platform
            for platform in post.platforms:
                if platform not in by_platform:
                    by_platform[platform] = {"views": [], "engagement": []}
                
                platform_analytics = [a for a in analytics if a.platform.value == platform]
                if platform_analytics:
                    platform_views = sum(a.views for a in platform_analytics)
                    platform_engagement = sum(a.likes + a.comments + a.shares for a in platform_analytics)
                    platform_eng_rate = (platform_engagement / platform_views * 100) if platform_views > 0 else 0
                    
                    by_platform[platform]["views"].append(platform_views)
                    by_platform[platform]["engagement"].append(platform_eng_rate)
            
            # Track recent performance for trend
            if post.published_at:
                recent_performance.append({
                    "date": post.published_at,
                    "engagement": engagement_rate,
                })
        
        if not views_list:
            return {"has_data": False, "post_count": len(posts)}
        
        # Calculate averages
        avg_views = statistics.mean(views_list)
        avg_engagement = statistics.mean(engagement_list)
        
        # Calculate platform averages
        platform_stats = {}
        for platform, data in by_platform.items():
            if data["views"]:
                platform_stats[platform] = {
                    "avg_views": statistics.mean(data["views"]),
                    "avg_engagement": statistics.mean(data["engagement"]),
                }
        
        # Determine trend
        trend = "stable"
        if len(recent_performance) >= 5:
            recent_performance.sort(key=lambda x: x["date"])
            first_half = [p["engagement"] for p in recent_performance[:len(recent_performance)//2]]
            second_half = [p["engagement"] for p in recent_performance[len(recent_performance)//2:]]
            
            if first_half and second_half:
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                
                if second_avg > first_avg * 1.1:
                    trend = "improving"
                elif second_avg < first_avg * 0.9:
                    trend = "declining"
        
        return {
            "has_data": True,
            "post_count": len(posts),
            "avg_views": avg_views,
            "avg_engagement": avg_engagement,
            "by_platform": platform_stats,
            "trend": trend,
        }
    
    def _get_template_performance_factor(self, template_id: UUID) -> float:
        """Get performance factor for a template."""
        # Get all videos using this template
        videos = self.db.query(Video).filter(Video.template_id == template_id).all()
        
        if not videos:
            return 1.0
        
        video_ids = [v.id for v in videos]
        
        # Get posts for these videos
        posts = self.db.query(Post).filter(
            and_(
                Post.video_id.in_(video_ids),
                Post.status == PostStatus.PUBLISHED,
            )
        ).all()
        
        if len(posts) < 3:
            return 1.0
        
        # Get analytics
        template_engagement = []
        for post in posts:
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).all()
            
            if analytics:
                total_views = sum(a.views for a in analytics)
                total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
                
                if total_views > 0:
                    template_engagement.append((total_engagement / total_views) * 100)
        
        if not template_engagement:
            return 1.0
        
        # Compare to overall average (simplified)
        template_avg = statistics.mean(template_engagement)
        
        # Normalize around 1.0 (template_avg / expected_avg)
        # For simplicity, assume 5% is the baseline engagement
        baseline = 5.0
        factor = template_avg / baseline
        
        # Clamp factor to reasonable range
        return max(0.5, min(2.0, factor))
    
    async def generate_suggestions(
        self,
        user_id: UUID,
        video_id: UUID,
        target_platforms: List[str],
        suggestions_service: SuggestionsService,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate performance prediction suggestion for a video.
        
        Args:
            user_id: User UUID
            video_id: Video UUID
            target_platforms: Target platforms
            suggestions_service: Service to create suggestions
            
        Returns:
            Created suggestion or None
        """
        prediction = self.predict_video_performance(user_id, video_id, target_platforms)
        
        if not prediction.get("success"):
            return None
        
        suggestion = suggestions_service.create_performance_prediction(
            user_id=user_id,
            video_id=video_id,
            predicted_views=prediction["total_predicted_views"],
            predicted_engagement=prediction["avg_predicted_engagement"],
            confidence=prediction["confidence"],
            factors=prediction["factors"],
        )
        
        return {
            "id": str(suggestion.id),
            "predicted_views": prediction["total_predicted_views"],
            "confidence": prediction["confidence"],
        }

