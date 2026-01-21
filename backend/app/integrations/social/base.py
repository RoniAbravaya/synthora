"""
Base Social Media Client

Abstract base class for social media platform integrations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OAuthConfig:
    """OAuth configuration for a platform."""
    
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]


@dataclass
class UserProfile:
    """User profile from a social platform."""
    
    platform_user_id: str
    username: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    followers_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PostResult:
    """Result of posting content to a platform."""
    
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AnalyticsData:
    """Analytics data from a platform."""
    
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    watch_time_seconds: int = 0
    avg_view_duration: float = 0.0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class BaseSocialClient(ABC):
    """
    Abstract base class for social media platform clients.
    
    All platform-specific clients should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the client."""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    # =========================================================================
    # OAuth Methods
    # =========================================================================
    
    @abstractmethod
    def get_authorization_url(
        self,
        config: OAuthConfig,
        state: str,
    ) -> str:
        """
        Get the OAuth authorization URL.
        
        Args:
            config: OAuth configuration
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        pass
    
    @abstractmethod
    async def exchange_code(
        self,
        config: OAuthConfig,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for tokens.
        
        Args:
            config: OAuth configuration
            code: Authorization code from callback
            
        Returns:
            Token data dict with access_token, refresh_token, expires_in
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(
        self,
        config: OAuthConfig,
        refresh_token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token.
        
        Args:
            config: OAuth configuration
            refresh_token: Refresh token
            
        Returns:
            New token data dict
        """
        pass
    
    # =========================================================================
    # Profile Methods
    # =========================================================================
    
    @abstractmethod
    async def get_user_profile(
        self,
        access_token: str,
    ) -> Optional[UserProfile]:
        """
        Get the authenticated user's profile.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            UserProfile instance
        """
        pass
    
    # =========================================================================
    # Posting Methods
    # =========================================================================
    
    @abstractmethod
    async def upload_video(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        **kwargs,
    ) -> PostResult:
        """
        Upload a video to the platform.
        
        Args:
            access_token: OAuth access token
            video_path: Path to video file
            title: Video title
            description: Video description
            **kwargs: Platform-specific options
            
        Returns:
            PostResult with upload status
        """
        pass
    
    # =========================================================================
    # Analytics Methods
    # =========================================================================
    
    @abstractmethod
    async def get_video_analytics(
        self,
        access_token: str,
        video_id: str,
    ) -> Optional[AnalyticsData]:
        """
        Get analytics for a specific video.
        
        Args:
            access_token: OAuth access token
            video_id: Platform-specific video ID
            
        Returns:
            AnalyticsData instance
        """
        pass
    
    @abstractmethod
    async def get_account_analytics(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Get account-level analytics.
        
        Args:
            access_token: OAuth access token
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Analytics data dictionary
        """
        pass

