"""
Posting Time Analyzer

Analyzes historical posting data to recommend optimal posting times.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.services.suggestions import SuggestionsService

logger = logging.getLogger(__name__)


class PostingTimeAnalyzer:
    """
    Analyzes posting patterns and engagement to recommend optimal posting times.
    
    Uses historical data to identify:
    - Best days of the week to post
    - Best hours to post
    - Platform-specific optimal times
    """
    
    MIN_POSTS_FOR_ANALYSIS = 5  # Minimum posts needed for meaningful analysis
    
    def __init__(self, db: Session):
        """
        Initialize the analyzer.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def analyze_user_posting_times(
        self,
        user_id: UUID,
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Analyze posting times for a user.
        
        Args:
            user_id: User UUID
            days: Number of days to analyze
            
        Returns:
            Analysis results with recommendations
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get published posts with analytics
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
                Post.published_at >= cutoff,
                Post.published_at.isnot(None),
            )
        ).all()
        
        if len(posts) < self.MIN_POSTS_FOR_ANALYSIS:
            return {
                "success": False,
                "reason": f"Need at least {self.MIN_POSTS_FOR_ANALYSIS} posts for analysis",
                "posts_analyzed": len(posts),
            }
        
        # Analyze by platform
        platform_analysis = {}
        
        for platform in ["youtube", "tiktok", "instagram", "facebook"]:
            platform_posts = [p for p in posts if platform in p.platforms]
            
            if len(platform_posts) < 3:
                continue
            
            analysis = self._analyze_platform_times(platform_posts, platform)
            if analysis:
                platform_analysis[platform] = analysis
        
        # Overall analysis
        overall = self._analyze_overall_times(posts)
        
        return {
            "success": True,
            "posts_analyzed": len(posts),
            "period_days": days,
            "overall": overall,
            "by_platform": platform_analysis,
        }
    
    def _analyze_platform_times(
        self,
        posts: List[Post],
        platform: str,
    ) -> Optional[Dict[str, Any]]:
        """Analyze posting times for a specific platform."""
        # Group posts by day and hour
        day_engagement = defaultdict(list)
        hour_engagement = defaultdict(list)
        day_hour_engagement = defaultdict(lambda: defaultdict(list))
        
        for post in posts:
            if not post.published_at:
                continue
            
            # Get analytics for this post on this platform
            analytics = self.db.query(Analytics).filter(
                and_(
                    Analytics.post_id == post.id,
                    Analytics.platform == platform,
                )
            ).order_by(Analytics.fetched_at.desc()).first()
            
            if not analytics:
                continue
            
            # Calculate engagement rate
            engagement = 0.0
            if analytics.views > 0:
                engagement = ((analytics.likes + analytics.comments + analytics.shares) / analytics.views) * 100
            
            day = post.published_at.weekday()
            hour = post.published_at.hour
            
            day_engagement[day].append(engagement)
            hour_engagement[hour].append(engagement)
            day_hour_engagement[day][hour].append(engagement)
        
        if not day_engagement:
            return None
        
        # Find best day
        avg_by_day = {
            day: sum(engs) / len(engs)
            for day, engs in day_engagement.items()
            if engs
        }
        
        best_day = max(avg_by_day, key=avg_by_day.get) if avg_by_day else 0
        
        # Find best hour
        avg_by_hour = {
            hour: sum(engs) / len(engs)
            for hour, engs in hour_engagement.items()
            if engs
        }
        
        best_hour = max(avg_by_hour, key=avg_by_hour.get) if avg_by_hour else 12
        
        # Find best day-hour combination
        best_combo = None
        best_combo_engagement = 0.0
        
        for day, hours in day_hour_engagement.items():
            for hour, engs in hours.items():
                if len(engs) >= 2:  # Need at least 2 data points
                    avg_eng = sum(engs) / len(engs)
                    if avg_eng > best_combo_engagement:
                        best_combo_engagement = avg_eng
                        best_combo = (day, hour)
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        return {
            "best_day": day_names[best_day],
            "best_day_index": best_day,
            "best_hour": best_hour,
            "best_combination": {
                "day": day_names[best_combo[0]] if best_combo else day_names[best_day],
                "hour": best_combo[1] if best_combo else best_hour,
                "avg_engagement": round(best_combo_engagement, 2),
            } if best_combo else None,
            "avg_engagement_by_day": {
                day_names[d]: round(e, 2) for d, e in avg_by_day.items()
            },
            "avg_engagement_by_hour": {
                str(h): round(e, 2) for h, e in sorted(avg_by_hour.items())
            },
            "posts_analyzed": len(posts),
        }
    
    def _analyze_overall_times(self, posts: List[Post]) -> Dict[str, Any]:
        """Analyze overall posting times across all platforms."""
        day_engagement = defaultdict(list)
        hour_engagement = defaultdict(list)
        
        for post in posts:
            if not post.published_at:
                continue
            
            # Get all analytics for this post
            analytics_list = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).all()
            
            if not analytics_list:
                continue
            
            # Sum up engagement across platforms
            total_views = sum(a.views for a in analytics_list)
            total_engagement = sum(a.likes + a.comments + a.shares for a in analytics_list)
            
            engagement_rate = 0.0
            if total_views > 0:
                engagement_rate = (total_engagement / total_views) * 100
            
            day = post.published_at.weekday()
            hour = post.published_at.hour
            
            day_engagement[day].append(engagement_rate)
            hour_engagement[hour].append(engagement_rate)
        
        # Find best day and hour
        avg_by_day = {
            day: sum(engs) / len(engs)
            for day, engs in day_engagement.items()
            if engs
        }
        
        avg_by_hour = {
            hour: sum(engs) / len(engs)
            for hour, engs in hour_engagement.items()
            if engs
        }
        
        best_day = max(avg_by_day, key=avg_by_day.get) if avg_by_day else 0
        best_hour = max(avg_by_hour, key=avg_by_hour.get) if avg_by_hour else 12
        
        # Calculate potential improvement
        current_avg = sum(sum(engs) for engs in day_engagement.values()) / max(1, sum(len(engs) for engs in day_engagement.values()))
        best_avg = avg_by_day.get(best_day, 0)
        improvement = ((best_avg - current_avg) / max(current_avg, 0.01)) * 100 if current_avg > 0 else 0
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        return {
            "best_day": day_names[best_day],
            "best_day_index": best_day,
            "best_hour": best_hour,
            "potential_improvement": round(max(0, improvement), 1),
            "current_avg_engagement": round(current_avg, 2),
            "best_avg_engagement": round(best_avg, 2),
        }
    
    def generate_suggestions(
        self,
        user_id: UUID,
        suggestions_service: SuggestionsService,
    ) -> List[Dict[str, Any]]:
        """
        Generate posting time suggestions for a user.
        
        Args:
            user_id: User UUID
            suggestions_service: Service to create suggestions
            
        Returns:
            List of created suggestions
        """
        analysis = self.analyze_user_posting_times(user_id)
        
        if not analysis.get("success"):
            return []
        
        created_suggestions = []
        
        # Create platform-specific suggestions
        for platform, data in analysis.get("by_platform", {}).items():
            if data.get("best_combination"):
                combo = data["best_combination"]
                suggestion = suggestions_service.create_posting_time_suggestion(
                    user_id=user_id,
                    platform=platform.title(),
                    recommended_day=combo["day"],
                    recommended_hour=combo["hour"],
                    engagement_boost=combo["avg_engagement"],
                    based_on_posts=data["posts_analyzed"],
                )
                created_suggestions.append({
                    "id": str(suggestion.id),
                    "platform": platform,
                    "type": "posting_time",
                })
        
        # Create overall suggestion if significant improvement possible
        overall = analysis.get("overall", {})
        if overall.get("potential_improvement", 0) > 10:
            suggestion = suggestions_service.create_suggestion(
                user_id=user_id,
                suggestion_type="optimal_time",
                title="Optimize your posting schedule",
                description=f"Posting on {overall['best_day']} at {overall['best_hour']}:00 could improve your engagement by {overall['potential_improvement']:.1f}%.",
                priority="high" if overall["potential_improvement"] > 25 else "medium",
                action_type="schedule_post",
                action_data={
                    "day": overall["best_day"],
                    "hour": overall["best_hour"],
                },
            )
            created_suggestions.append({
                "id": str(suggestion.id),
                "type": "overall_posting_time",
            })
        
        return created_suggestions

