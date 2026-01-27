"""
Post Model

Represents a social media post (scheduled or published) for a video.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video
    from app.models.social_account import SocialAccount
    from app.models.analytics import Analytics


class PostStatus(str, enum.Enum):
    """
    Post status values.
    
    - draft: Saved but not scheduled or posted
    - scheduled: Queued for future posting
    - publishing: Currently being posted
    - published: Successfully posted
    - failed: Posting failed
    - cancelled: User cancelled scheduled post
    """
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Post(Base, UUIDMixin, TimestampMixin):
    """
    Post model for social media posts.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        video_id: Foreign key to video
        social_account_id: Foreign key to social account
        platform: Target platform (stored as string)
        platform_post_id: Platform-specific post ID
        caption: Post caption/description
        hashtags: List of hashtags
        status: Current post status (stored as string)
        scheduled_at: When the post is scheduled for
        published_at: When the post was published
        post_url: URL to the post on the platform
        error_message: Error message if failed
        retry_count: Number of retry attempts
        platform_config: Platform-specific settings (JSON)
        
    Relationships:
        user: The user who created this post
        video: The video being posted
        social_account: The social account to post to
        analytics: Analytics data for this post
    """
    
    __tablename__ = "posts"
    
    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to video"
    )
    social_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to social account"
    )
    
    # Platform Info - stored as string in DB (not PostgreSQL ENUM)
    platform = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Target platform"
    )
    platform_post_id = Column(
        String(255),
        nullable=True,
        doc="Platform-specific post ID"
    )
    
    # Content
    caption = Column(
        Text,
        nullable=True,
        doc="Post caption/description"
    )
    hashtags = Column(
        ARRAY(String(100)),
        nullable=True,
        doc="List of hashtags"
    )
    
    # Status - stored as string in DB (not PostgreSQL ENUM)
    status = Column(
        String(20),
        default="draft",
        nullable=False,
        index=True,
        doc="Current post status"
    )
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="When the post is scheduled for"
    )
    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the post was published"
    )
    
    # Platform Response
    post_url = Column(
        Text,
        nullable=True,
        doc="URL to the post on the platform"
    )
    
    # Error Tracking
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    
    # Platform-specific config
    platform_config = Column(
        JSONB,
        nullable=True,
        doc="Platform-specific settings"
    )
    
    # Relationships
    user = relationship("User", back_populates="posts")
    video = relationship("Video", back_populates="posts")
    social_account = relationship("SocialAccount", back_populates="posts")
    analytics = relationship("Analytics", back_populates="post", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Post(id={self.id}, platform={self.platform}, status={self.status})>"
    
    # Aliases for backwards compatibility
    @property
    def post_id(self) -> Optional[str]:
        """Alias for platform_post_id."""
        return self.platform_post_id
    
    @property
    def platform_specific(self) -> Optional[dict]:
        """Alias for platform_config."""
        return self.platform_config
    
    @property
    def title(self) -> Optional[str]:
        """
        Get post title derived from caption.
        
        Returns the first line of the caption (up to 100 chars) or None.
        This provides backwards compatibility where 'title' is expected.
        """
        if not self.caption:
            return None
        # Get first line of caption as title
        first_line = self.caption.split('\n')[0].strip()
        # Limit to 100 characters
        if len(first_line) > 100:
            return first_line[:97] + "..."
        return first_line if first_line else None
    
    @property
    def description(self) -> Optional[str]:
        """
        Alias for caption for backwards compatibility.
        """
        return self.caption
    
    @property
    def platforms(self) -> List[str]:
        """
        Get list of platforms (returns single-item list with this post's platform).
        
        For backwards compatibility where posts were expected to have multiple platforms.
        """
        return [self.platform] if self.platform else []
    
    @property
    def error_log(self) -> Optional[dict]:
        """Get error info as dict."""
        if self.error_message:
            return {"message": self.error_message}
        return None
    
    @property
    def is_published(self) -> bool:
        """Check if post is published."""
        return self.status == "published"
    
    @property
    def is_scheduled(self) -> bool:
        """Check if post is scheduled."""
        return self.status == "scheduled"
    
    @property
    def is_due(self) -> bool:
        """Check if scheduled post is due for publishing."""
        if not self.is_scheduled or not self.scheduled_at:
            return False
        return datetime.utcnow() >= self.scheduled_at
    
    @property
    def can_edit(self) -> bool:
        """Check if post can be edited."""
        return self.status in ("draft", "scheduled")
    
    @property
    def can_cancel(self) -> bool:
        """Check if post can be cancelled."""
        return self.status == "scheduled"
    
    @property
    def formatted_hashtags(self) -> str:
        """Get hashtags as a formatted string."""
        if not self.hashtags:
            return ""
        return " ".join(f"#{tag.lstrip('#')}" for tag in self.hashtags)
    
    @property
    def full_caption(self) -> str:
        """Get caption with hashtags appended."""
        parts = []
        if self.caption:
            parts.append(self.caption)
        if self.hashtags:
            parts.append(self.formatted_hashtags)
        return "\n\n".join(parts)
    
    def mark_publishing(self) -> None:
        """Mark post as currently being published."""
        self.status = "publishing"
    
    def mark_published(self, post_id: str, post_url: str) -> None:
        """
        Mark post as successfully published.
        
        Args:
            post_id: Platform-specific post ID
            post_url: URL to the post
        """
        self.status = "published"
        self.published_at = datetime.utcnow()
        self.platform_post_id = post_id
        self.post_url = post_url
    
    def mark_failed(self, error_message: str, error_details: dict = None) -> None:
        """
        Mark post as failed.
        
        Args:
            error_message: Human-readable error message
            error_details: Additional error details
        """
        self.status = "failed"
        self.retry_count += 1
        self.error_message = error_message
    
    def cancel(self) -> None:
        """Cancel a scheduled post."""
        if self.can_cancel:
            self.status = "cancelled"
