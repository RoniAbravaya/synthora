"""
Base Publisher

Abstract base class for platform publishers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of publishing to a platform."""
    
    success: bool
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "platform": self.platform,
            "post_id": self.post_id,
            "post_url": self.post_url,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class PublishRequest:
    """Request to publish a video."""
    
    video_path: str
    video_url: Optional[str]  # For platforms requiring URL
    title: str
    description: str
    hashtags: List[str]
    access_token: str
    platform_overrides: Optional[Dict[str, Any]] = None


class BasePublisher(ABC):
    """
    Abstract base class for platform publishers.
    
    Each platform publisher should implement:
    - publish(): Upload and publish a video
    - validate_content(): Validate content meets platform requirements
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Get the platform name."""
        pass
    
    @property
    @abstractmethod
    def max_title_length(self) -> int:
        """Maximum title length for the platform."""
        pass
    
    @property
    @abstractmethod
    def max_description_length(self) -> int:
        """Maximum description length for the platform."""
        pass
    
    @property
    @abstractmethod
    def max_hashtags(self) -> int:
        """Maximum number of hashtags."""
        pass
    
    @abstractmethod
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a video to the platform.
        
        Args:
            request: Publish request with video and metadata
            
        Returns:
            PublishResult with outcome
        """
        pass
    
    def validate_content(
        self,
        title: str,
        description: str,
        hashtags: List[str],
    ) -> tuple[bool, List[str]]:
        """
        Validate content meets platform requirements.
        
        Args:
            title: Video title
            description: Video description
            hashtags: List of hashtags
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        if len(title) > self.max_title_length:
            issues.append(f"Title exceeds {self.max_title_length} characters")
        
        if len(description) > self.max_description_length:
            issues.append(f"Description exceeds {self.max_description_length} characters")
        
        if len(hashtags) > self.max_hashtags:
            issues.append(f"Too many hashtags (max {self.max_hashtags})")
        
        return len(issues) == 0, issues
    
    def format_caption(
        self,
        title: str,
        description: str,
        hashtags: List[str],
    ) -> str:
        """
        Format caption for platforms that use a single text field.
        
        Args:
            title: Video title
            description: Video description
            hashtags: List of hashtags
            
        Returns:
            Formatted caption string
        """
        parts = []
        
        if title:
            parts.append(title)
        
        if description:
            parts.append(description)
        
        if hashtags:
            hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
            parts.append(hashtag_str)
        
        return "\n\n".join(parts)
    
    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."

