"""
Analytics Service

Business logic for fetching, storing, and aggregating analytics data.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.analytics import Analytics
from app.models.post import Post, PostStatus
from app.models.video import Video
from app.models.social_account import SocialAccount, SocialPlatform

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service class for analytics management.
    
    Handles:
    - Storing and retrieving analytics data
    - Aggregating metrics across platforms
    - Time-series data generation
    - Top performers identification
    - Posting heatmap generation
    """
    
    def __init__(self, db: Session):
        """
        Initialize the analytics service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_post_analytics(
        self,
        post_id: UUID,
        platform: Optional[SocialPlatform] = None,
    ) -> List[Analytics]:
        """
        Get analytics for a specific post.
        
        Args:
            post_id: Post UUID
            platform: Optional platform filter
            
        Returns:
            List of Analytics records
        """
        query = self.db.query(Analytics).filter(Analytics.post_id == post_id)
        
        if platform:
            query = query.filter(Analytics.platform == platform)
        
        return query.order_by(Analytics.fetched_at.desc()).all()
    
    def get_latest_post_analytics(
        self,
        post_id: UUID,
        platform: SocialPlatform,
    ) -> Optional[Analytics]:
        """Get the most recent analytics for a post on a platform."""
        return self.db.query(Analytics).filter(
            and_(
                Analytics.post_id == post_id,
                Analytics.platform == platform,
            )
        ).order_by(Analytics.fetched_at.desc()).first()
    
    def get_user_analytics_overview(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get analytics overview for a user.
        
        Args:
            user_id: User UUID
            days: Number of days to look back
            
        Returns:
            Dictionary with aggregated metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get all posts for user
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
            )
        ).all()
        
        post_ids = [p.id for p in posts]
        
        if not post_ids:
            return self._empty_overview()
        
        # Get latest analytics for each post/platform
        analytics_data = []
        for post_id in post_ids:
            for platform in SocialPlatform:
                latest = self.get_latest_post_analytics(post_id, platform)
                if latest:
                    analytics_data.append(latest)
        
        # Aggregate metrics
        total_views = sum(a.views for a in analytics_data)
        total_likes = sum(a.likes for a in analytics_data)
        total_comments = sum(a.comments for a in analytics_data)
        total_shares = sum(a.shares for a in analytics_data)
        total_saves = sum(a.saves for a in analytics_data)
        
        # Calculate engagement rate
        engagement_rate = 0.0
        if total_views > 0:
            engagement_rate = ((total_likes + total_comments + total_shares) / total_views) * 100
        
        # Group by platform
        by_platform = defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0, "shares": 0})
        for a in analytics_data:
            by_platform[a.platform]["views"] += a.views
            by_platform[a.platform]["likes"] += a.likes
            by_platform[a.platform]["comments"] += a.comments
            by_platform[a.platform]["shares"] += a.shares
        
        return {
            "period_days": days,
            "total_posts": len(posts),
            "summary": {
                "views": total_views,
                "likes": total_likes,
                "comments": total_comments,
                "shares": total_shares,
                "saves": total_saves,
                "engagement_rate": round(engagement_rate, 2),
            },
            "by_platform": dict(by_platform),
        }
    
    def _empty_overview(self) -> Dict[str, Any]:
        """Return empty overview structure."""
        return {
            "period_days": 0,
            "total_posts": 0,
            "summary": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "saves": 0,
                "engagement_rate": 0.0,
            },
            "by_platform": {},
        }
    
    def get_time_series(
        self,
        user_id: UUID,
        metric: str,
        days: int = 30,
        platform: Optional[SocialPlatform] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get time-series data for a metric.
        
        Args:
            user_id: User UUID
            metric: Metric name (views, likes, comments, shares)
            days: Number of days
            platform: Optional platform filter
            
        Returns:
            List of {date, value} dictionaries
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get user's posts
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
            )
        ).all()
        
        post_ids = [p.id for p in posts]
        
        if not post_ids:
            return []
        
        # Query analytics grouped by date
        query = self.db.query(
            func.date(Analytics.fetched_at).label("date"),
            func.sum(getattr(Analytics, metric)).label("value"),
        ).filter(
            and_(
                Analytics.post_id.in_(post_ids),
                Analytics.fetched_at >= cutoff,
            )
        )
        
        if platform:
            query = query.filter(Analytics.platform == platform)
        
        results = query.group_by(func.date(Analytics.fetched_at)).order_by("date").all()
        
        return [
            {"date": str(r.date), "value": int(r.value or 0)}
            for r in results
        ]
    
    def get_top_performing(
        self,
        user_id: UUID,
        metric: str = "views",
        limit: int = 10,
        platform: Optional[SocialPlatform] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing posts by a metric.
        
        Args:
            user_id: User UUID
            metric: Metric to sort by
            limit: Number of results
            platform: Optional platform filter
            
        Returns:
            List of top performing posts with metrics
        """
        # Get user's posts
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
            )
        ).all()
        
        post_ids = [p.id for p in posts]
        
        if not post_ids:
            return []
        
        # Get latest analytics for each post
        results = []
        for post in posts:
            # Get video info
            video = self.db.query(Video).filter(Video.id == post.video_id).first()
            
            # Get analytics
            query = self.db.query(Analytics).filter(Analytics.post_id == post.id)
            if platform:
                query = query.filter(Analytics.platform == platform)
            
            analytics_list = query.order_by(Analytics.fetched_at.desc()).all()
            
            if not analytics_list:
                continue
            
            # Aggregate across platforms
            total_views = sum(a.views for a in analytics_list)
            total_likes = sum(a.likes for a in analytics_list)
            total_comments = sum(a.comments for a in analytics_list)
            total_shares = sum(a.shares for a in analytics_list)
            
            results.append({
                "post_id": str(post.id),
                "video_id": str(post.video_id),
                "title": post.title or (video.title if video else "Untitled"),
                "thumbnail_url": video.thumbnail_url if video else None,
                "platforms": post.platforms,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "metrics": {
                    "views": total_views,
                    "likes": total_likes,
                    "comments": total_comments,
                    "shares": total_shares,
                },
            })
        
        # Sort by metric
        results.sort(key=lambda x: x["metrics"].get(metric, 0), reverse=True)
        
        return results[:limit]
    
    def get_posting_heatmap(
        self,
        user_id: UUID,
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Get posting heatmap data (best times to post).
        
        Args:
            user_id: User UUID
            days: Number of days to analyze
            
        Returns:
            Heatmap data by day of week and hour
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get published posts with their analytics
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
                Post.published_at >= cutoff,
            )
        ).all()
        
        # Initialize heatmap (day 0-6, hour 0-23)
        heatmap = defaultdict(lambda: defaultdict(lambda: {"posts": 0, "avg_engagement": 0.0}))
        
        for post in posts:
            if not post.published_at:
                continue
            
            day_of_week = post.published_at.weekday()
            hour = post.published_at.hour
            
            # Get engagement for this post
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).all()
            
            total_engagement = sum(
                a.likes + a.comments + a.shares
                for a in analytics
            )
            total_views = sum(a.views for a in analytics)
            
            engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
            
            # Update heatmap
            cell = heatmap[day_of_week][hour]
            current_posts = cell["posts"]
            current_avg = cell["avg_engagement"]
            
            # Calculate new average
            new_avg = ((current_avg * current_posts) + engagement_rate) / (current_posts + 1)
            
            heatmap[day_of_week][hour] = {
                "posts": current_posts + 1,
                "avg_engagement": round(new_avg, 2),
            }
        
        # Convert to serializable format
        result = {}
        for day in range(7):
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day]
            result[day_name] = {
                str(hour): heatmap[day][hour]
                for hour in range(24)
            }
        
        return {
            "period_days": days,
            "heatmap": result,
        }
    
    # =========================================================================
    # Store Methods
    # =========================================================================
    
    def store_analytics(
        self,
        post_id: UUID,
        platform: SocialPlatform,
        platform_post_id: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        saves: int = 0,
        watch_time_seconds: int = 0,
        avg_view_duration: float = 0.0,
        reach: int = 0,
        impressions: int = 0,
        click_through_rate: float = 0.0,
        follower_change: int = 0,
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> Analytics:
        """
        Store analytics data for a post.
        
        Args:
            post_id: Post UUID
            platform: Platform
            platform_post_id: Platform-specific post ID
            views: View count
            likes: Like count
            comments: Comment count
            shares: Share count
            saves: Save/bookmark count
            watch_time_seconds: Total watch time
            avg_view_duration: Average view duration
            reach: Reach count
            impressions: Impression count
            click_through_rate: CTR percentage
            follower_change: Follower change
            raw_data: Raw API response
            
        Returns:
            Created Analytics instance
        """
        # Calculate engagement rate
        engagement_rate = 0.0
        if views > 0:
            engagement_rate = ((likes + comments + shares) / views) * 100
        
        analytics = Analytics(
            post_id=post_id,
            platform=platform,
            platform_post_id=platform_post_id,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            watch_time_seconds=watch_time_seconds,
            avg_view_duration=avg_view_duration,
            reach=reach,
            impressions=impressions,
            engagement_rate=round(engagement_rate, 2),
            click_through_rate=click_through_rate,
            follower_change=follower_change,
            raw_data=raw_data,
            fetched_at=datetime.utcnow(),
        )
        
        self.db.add(analytics)
        self.db.commit()
        self.db.refresh(analytics)
        
        logger.info(f"Stored analytics for post {post_id} on {platform.value}")
        return analytics
    
    def update_post_analytics(
        self,
        analytics: Analytics,
        **kwargs,
    ) -> Analytics:
        """Update existing analytics record."""
        for key, value in kwargs.items():
            if hasattr(analytics, key) and value is not None:
                setattr(analytics, key, value)
        
        # Recalculate engagement rate
        if analytics.views > 0:
            analytics.engagement_rate = round(
                ((analytics.likes + analytics.comments + analytics.shares) / analytics.views) * 100,
                2
            )
        
        analytics.fetched_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(analytics)
        
        return analytics
    
    # =========================================================================
    # Platform Comparison
    # =========================================================================
    
    def get_platform_comparison(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Compare performance across platforms.
        
        Args:
            user_id: User UUID
            days: Number of days
            
        Returns:
            Platform comparison data
        """
        overview = self.get_user_analytics_overview(user_id, days)
        
        platforms_data = []
        for platform_name, metrics in overview["by_platform"].items():
            views = metrics.get("views", 0)
            likes = metrics.get("likes", 0)
            comments = metrics.get("comments", 0)
            shares = metrics.get("shares", 0)
            
            engagement_rate = 0.0
            if views > 0:
                engagement_rate = ((likes + comments + shares) / views) * 100
            
            platforms_data.append({
                "platform": platform_name,
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": round(engagement_rate, 2),
            })
        
        # Sort by views
        platforms_data.sort(key=lambda x: x["views"], reverse=True)
        
        return {
            "period_days": days,
            "platforms": platforms_data,
        }


def get_analytics_service(db: Session) -> AnalyticsService:
    """Factory function to create an AnalyticsService instance."""
    return AnalyticsService(db)

