"""
Analytics Model

Stores performance metrics fetched from social media platforms.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.post import Post


class Analytics(Base, UUIDMixin):
    """
    Analytics model for storing post performance metrics.
    
    Attributes:
        id: Unique identifier (UUID)
        post_id: Foreign key to post
        
        # Primary Metrics (High Priority)
        views: Number of views
        likes: Number of likes
        shares: Number of shares
        
        # Secondary Metrics (Medium Priority)
        comments: Number of comments
        watch_time_seconds: Total watch time in seconds
        avg_view_duration: Average view duration in seconds
        retention_rate: Percentage of video watched (0-100)
        
        # Additional Metrics (Lower Priority)
        saves: Number of saves/bookmarks
        click_through_rate: CTR percentage
        reach: Unique accounts reached
        impressions: Total impressions
        follower_change: Net follower change from this post
        
        # Tracking
        fetched_at: When these metrics were fetched
        
    Relationships:
        post: The post these analytics belong to
    """
    
    __tablename__ = "analytics"
    
    # Foreign Key
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Foreign key to post"
    )
    
    # Primary Metrics (High Priority)
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
    shares = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of shares"
    )
    
    # Secondary Metrics (Medium Priority)
    comments = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of comments"
    )
    watch_time_seconds = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total watch time in seconds"
    )
    avg_view_duration = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average view duration in seconds"
    )
    retention_rate = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Percentage of video watched (0-100)"
    )
    
    # Additional Metrics (Lower Priority)
    saves = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of saves/bookmarks"
    )
    click_through_rate = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="CTR percentage"
    )
    reach = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Unique accounts reached"
    )
    impressions = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total impressions"
    )
    follower_change = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Net follower change from this post"
    )
    
    # Tracking
    fetched_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="When these metrics were fetched"
    )
    
    # Relationship
    post = relationship("Post", back_populates="analytics")
    
    def __repr__(self) -> str:
        return f"<Analytics(id={self.id}, post_id={self.post_id}, views={self.views})>"
    
    @property
    def engagement_count(self) -> int:
        """Get total engagement (likes + comments + shares + saves)."""
        return self.likes + self.comments + self.shares + self.saves
    
    @property
    def engagement_rate(self) -> float:
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
        avg_view_duration: Optional[float] = None,
        retention_rate: Optional[float] = None,
        saves: Optional[int] = None,
        click_through_rate: Optional[float] = None,
        reach: Optional[int] = None,
        impressions: Optional[int] = None,
        follower_change: Optional[int] = None,
    ) -> None:
        """
        Update metrics with new values from platform API.
        Only updates fields that are provided (not None).
        
        Args:
            views: New view count
            likes: New like count
            shares: New share count
            comments: New comment count
            watch_time_seconds: New total watch time
            avg_view_duration: New average view duration
            retention_rate: New retention rate
            saves: New save count
            click_through_rate: New CTR
            reach: New reach count
            impressions: New impression count
            follower_change: New follower change
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
        if avg_view_duration is not None:
            self.avg_view_duration = avg_view_duration
        if retention_rate is not None:
            self.retention_rate = retention_rate
        if saves is not None:
            self.saves = saves
        if click_through_rate is not None:
            self.click_through_rate = click_through_rate
        if reach is not None:
            self.reach = reach
        if impressions is not None:
            self.impressions = impressions
        if follower_change is not None:
            self.follower_change = follower_change
        
        # Update fetch timestamp
        self.fetched_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert analytics to dictionary."""
        return {
            "views": self.views,
            "likes": self.likes,
            "shares": self.shares,
            "comments": self.comments,
            "watch_time_seconds": self.watch_time_seconds,
            "avg_view_duration": self.avg_view_duration,
            "retention_rate": self.retention_rate,
            "saves": self.saves,
            "click_through_rate": self.click_through_rate,
            "reach": self.reach,
            "impressions": self.impressions,
            "follower_change": self.follower_change,
            "engagement_count": self.engagement_count,
            "engagement_rate": self.engagement_rate,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }

