"""
Analytics Model

Stores performance metrics fetched from social media platforms.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Analytics(Base, UUIDMixin, TimestampMixin):
    """
    Analytics model for storing post performance metrics.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        post_id: Foreign key to post
        user_id: Foreign key to user
        platform: Platform the analytics are for
        views: Number of views
        likes: Number of likes
        comments: Number of comments
        shares: Number of shares
        saves: Number of saves/bookmarks
        watch_time_seconds: Total watch time in seconds
        avg_watch_percentage: Average percentage of video watched
        engagement_rate: Engagement rate percentage
        reach: Unique accounts reached
        impressions: Total impressions
        clicks: Number of clicks
        raw_data: Raw analytics data from platform API
        fetched_at: When these metrics were fetched
        
    Relationships:
        post: The post these analytics belong to
        user: The user who owns this analytics data
    """
    
    __tablename__ = "analytics"
    
    # Foreign Keys
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to post"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    
    # Platform - stored as string
    platform = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Platform the analytics are for"
    )
    
    # Primary Metrics
    views = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of views"
    )
    likes = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of likes"
    )
    comments = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of comments"
    )
    shares = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of shares"
    )
    saves = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of saves/bookmarks"
    )
    
    # Watch Time Metrics
    watch_time_seconds = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total watch time in seconds"
    )
    avg_watch_percentage = Column(
        Float,
        nullable=True,
        doc="Average percentage of video watched"
    )
    
    # Engagement
    engagement_rate = Column(
        Float,
        nullable=True,
        doc="Engagement rate percentage"
    )
    
    # Reach Metrics
    reach = Column(
        Integer,
        nullable=True,
        doc="Unique accounts reached"
    )
    impressions = Column(
        Integer,
        nullable=True,
        doc="Total impressions"
    )
    clicks = Column(
        Integer,
        nullable=True,
        doc="Number of clicks"
    )
    
    # Raw Data
    raw_data = Column(
        JSONB,
        nullable=True,
        doc="Raw analytics data from platform API"
    )
    
    # Tracking
    fetched_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="When these metrics were fetched"
    )
    
    # Relationships
    post = relationship("Post", back_populates="analytics")
    user = relationship("User", back_populates="analytics")
    
    def __repr__(self) -> str:
        return f"<Analytics(id={self.id}, post_id={self.post_id}, platform={self.platform}, views={self.views})>"
    
    # Aliases for backwards compatibility
    @property
    def avg_view_duration(self) -> Optional[float]:
        """Alias - calculate from watch_time_seconds and views."""
        if self.views and self.watch_time_seconds:
            return self.watch_time_seconds / self.views
        return None
    
    @property
    def retention_rate(self) -> Optional[float]:
        """Alias for avg_watch_percentage."""
        return self.avg_watch_percentage
    
    @property
    def click_through_rate(self) -> Optional[float]:
        """Calculate CTR from clicks and impressions."""
        if self.impressions and self.clicks:
            return (self.clicks / self.impressions) * 100
        return None
    
    @property
    def follower_change(self) -> int:
        """Backwards compatibility - always 0 as not tracked in DB."""
        return 0
    
    @property
    def engagement_count(self) -> int:
        """Get total engagement (likes + comments + shares + saves)."""
        return self.likes + self.comments + self.shares + self.saves
    
    @property
    def calculated_engagement_rate(self) -> float:
        """
        Calculate engagement rate as percentage.
        Engagement rate = (engagement / views) * 100
        """
        if self.views == 0:
            return 0.0
        return (self.engagement_count / self.views) * 100
    
    def update_metrics(
        self,
        views: Optional[int] = None,
        likes: Optional[int] = None,
        shares: Optional[int] = None,
        comments: Optional[int] = None,
        watch_time_seconds: Optional[int] = None,
        avg_watch_percentage: Optional[float] = None,
        engagement_rate: Optional[float] = None,
        saves: Optional[int] = None,
        reach: Optional[int] = None,
        impressions: Optional[int] = None,
        clicks: Optional[int] = None,
        raw_data: Optional[dict] = None,
    ) -> None:
        """
        Update metrics with new values from platform API.
        Only updates fields that are provided (not None).
        """
        if views is not None:
            self.views = views
        if likes is not None:
            self.likes = likes
        if shares is not None:
            self.shares = shares
        if comments is not None:
            self.comments = comments
        if watch_time_seconds is not None:
            self.watch_time_seconds = watch_time_seconds
        if avg_watch_percentage is not None:
            self.avg_watch_percentage = avg_watch_percentage
        if engagement_rate is not None:
            self.engagement_rate = engagement_rate
        if saves is not None:
            self.saves = saves
        if reach is not None:
            self.reach = reach
        if impressions is not None:
            self.impressions = impressions
        if clicks is not None:
            self.clicks = clicks
        if raw_data is not None:
            self.raw_data = raw_data
        
        # Update fetch timestamp
        self.fetched_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert analytics to dictionary."""
        return {
            "platform": self.platform,
            "views": self.views,
            "likes": self.likes,
            "shares": self.shares,
            "comments": self.comments,
            "watch_time_seconds": self.watch_time_seconds,
            "avg_watch_percentage": self.avg_watch_percentage,
            "engagement_rate": self.engagement_rate,
            "saves": self.saves,
            "reach": self.reach,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "engagement_count": self.engagement_count,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
