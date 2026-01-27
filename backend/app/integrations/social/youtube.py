"""
YouTube Integration

OAuth and API client for YouTube.
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlencode

import httpx

from app.integrations.social.base import (
    BaseSocialClient,
    OAuthConfig,
    UserProfile,
    PostResult,
    AnalyticsData,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class YouTubeClient(BaseSocialClient):
    """
    YouTube OAuth and API client.
    
    Uses Google OAuth 2.0 for authentication and the YouTube Data API
    for video uploads and analytics.
    """
    
    # OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    # API endpoints
    API_BASE = "https://www.googleapis.com/youtube/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    
    # Required scopes
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]
    
    def __init__(self):
        """Initialize the YouTube client."""
        super().__init__()
        settings = get_settings()
        
        self.default_config = OAuthConfig(
            client_id=settings.YOUTUBE_CLIENT_ID or "",
            client_secret=settings.YOUTUBE_CLIENT_SECRET or "",
            redirect_uri=settings.youtube_redirect_uri,
            scopes=self.DEFAULT_SCOPES,
        )
    
    # =========================================================================
    # OAuth Methods
    # =========================================================================
    
    def get_authorization_url(
        self,
        config: Optional[OAuthConfig] = None,
        state: str = "",
    ) -> str:
        """Get the Google OAuth authorization URL."""
        config = config or self.default_config
        
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Always show consent screen
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        config: Optional[OAuthConfig] = None,
        code: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        config = config or self.default_config
        
        try:
            response = await self.client.post(
                self.TOKEN_URL,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config.redirect_uri,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube token exchange failed: {response.text}")
                return None
            
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 3600),
                "token_type": data.get("token_type", "Bearer"),
                "scope": data.get("scope", ""),
            }
            
        except Exception as e:
            logger.exception("YouTube token exchange error")
            return None
    
    async def refresh_access_token(
        self,
        config: Optional[OAuthConfig] = None,
        refresh_token: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        config = config or self.default_config
        
        try:
            response = await self.client.post(
                self.TOKEN_URL,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube token refresh failed: {response.text}")
                return None
            
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_in": data.get("expires_in", 3600),
                "token_type": data.get("token_type", "Bearer"),
            }
            
        except Exception as e:
            logger.exception("YouTube token refresh error")
            return None
    
    # =========================================================================
    # Profile Methods
    # =========================================================================
    
    async def get_user_profile(
        self,
        access_token: str,
    ) -> Optional[UserProfile]:
        """Get the authenticated user's YouTube channel."""
        try:
            response = await self.client.get(
                f"{self.API_BASE}/channels",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "snippet,statistics",
                    "mine": "true",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube profile fetch failed: {response.text}")
                return None
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return None
            
            channel = items[0]
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            
            return UserProfile(
                platform_user_id=channel["id"],
                username=snippet.get("customUrl", snippet.get("title", "")),
                display_name=snippet.get("title"),
                profile_url=f"https://youtube.com/channel/{channel['id']}",
                avatar_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                followers_count=int(statistics.get("subscriberCount", 0)),
                metadata={
                    "view_count": int(statistics.get("viewCount", 0)),
                    "video_count": int(statistics.get("videoCount", 0)),
                },
            )
            
        except Exception as e:
            logger.exception("YouTube profile fetch error")
            return None
    
    # =========================================================================
    # Posting Methods
    # =========================================================================
    
    async def upload_video(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",
        category_id: str = "22",  # People & Blogs
        **kwargs,
    ) -> PostResult:
        """
        Upload a video to YouTube.
        
        Args:
            access_token: OAuth access token
            video_path: Path to video file or URL
            title: Video title
            description: Video description
            tags: Video tags
            privacy_status: public, private, or unlisted
            category_id: YouTube category ID
            
        Returns:
            PostResult with upload status
        """
        import tempfile
        import json
        
        logger.info(f"=== YOUTUBE UPLOAD STARTED ===")
        logger.info(f"Title: {title}, Privacy: {privacy_status}, Tags: {tags}")
        logger.info(f"Video path: {video_path[:150] if video_path else 'None'}...")
        logger.info(f"Access token length: {len(access_token) if access_token else 0}")
        
        try:
            video_data = None
            video_filename = "video.mp4"
            
            # Check if video_path is a URL
            if video_path.startswith("http://") or video_path.startswith("https://"):
                logger.info(f"Downloading video from URL...")
                # Download video from URL
                try:
                    download_response = await self.client.get(
                        video_path,
                        timeout=300.0,  # 5 minutes for large videos
                    )
                    if download_response.status_code != 200:
                        logger.error(f"Download failed: HTTP {download_response.status_code}")
                        return PostResult(
                            success=False,
                            error=f"Failed to download video: HTTP {download_response.status_code}",
                        )
                    video_data = download_response.content
                    logger.info(f"Downloaded video: {len(video_data)} bytes")
                except Exception as e:
                    logger.exception(f"Error downloading video: {e}")
                    return PostResult(success=False, error=f"Failed to download video: {str(e)}")
            else:
                # Read from local file
                if not os.path.exists(video_path):
                    logger.error(f"Video file not found at path: {video_path}")
                    return PostResult(success=False, error="Video file not found")
                
                with open(video_path, "rb") as f:
                    video_data = f.read()
                video_filename = os.path.basename(video_path)
                logger.info(f"Read video from local file: {len(video_data)} bytes")
            
            if not video_data:
                logger.error("No video data to upload")
                return PostResult(success=False, error="No video data to upload")
            
            logger.info(f"Uploading {len(video_data)} bytes to YouTube...")
            
            # Create video metadata
            metadata = {
                "snippet": {
                    "title": title[:100],  # YouTube limit
                    "description": description[:5000],
                    "tags": tags or [],
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }
            
            # Use resumable upload for reliability
            # Step 1: Initialize upload
            init_response = await self.client.post(
                f"{self.UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Length": str(len(video_data)),
                    "X-Upload-Content-Type": "video/*",
                },
                content=json.dumps(metadata),
                timeout=60.0,
            )
            
            if init_response.status_code != 200:
                logger.error(f"YouTube upload init failed: {init_response.status_code}")
                logger.error(f"Response: {init_response.text[:500] if init_response.text else 'No response body'}")
                return PostResult(
                    success=False,
                    error=f"Upload initialization failed: HTTP {init_response.status_code} - {init_response.text[:200] if init_response.text else 'Unknown error'}",
                )
            
            # Get the upload URL from the Location header
            upload_url = init_response.headers.get("Location")
            if not upload_url:
                return PostResult(
                    success=False,
                    error="No upload URL returned from YouTube",
                )
            
            logger.info(f"Uploading video data ({len(video_data)} bytes)...")
            
            # Step 2: Upload the video data
            upload_response = await self.client.put(
                upload_url,
                headers={
                    "Content-Type": "video/*",
                    "Content-Length": str(len(video_data)),
                },
                content=video_data,
                timeout=600.0,  # 10 minutes for upload
            )
            
            if upload_response.status_code not in [200, 201]:
                logger.error(f"YouTube video upload failed: {upload_response.status_code} - {upload_response.text}")
                return PostResult(
                    success=False,
                    error=f"Video upload failed: {upload_response.text}",
                )
            
            data = upload_response.json()
            video_id = data.get("id")
            
            logger.info(f"YouTube upload successful! Video ID: {video_id}")
            
            return PostResult(
                success=True,
                post_id=video_id,
                post_url=f"https://youtube.com/watch?v={video_id}",
                metadata={"status": data.get("status", {})},
            )
            
        except Exception as e:
            logger.exception("YouTube upload error")
            return PostResult(success=False, error=str(e))
    
    # =========================================================================
    # Analytics Methods
    # =========================================================================
    
    async def get_video_analytics(
        self,
        access_token: str,
        video_id: str,
    ) -> Optional[AnalyticsData]:
        """Get analytics for a specific video."""
        try:
            # Get video statistics
            response = await self.client.get(
                f"{self.API_BASE}/videos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "statistics",
                    "id": video_id,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube analytics fetch failed: {response.text}")
                return None
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return None
            
            stats = items[0].get("statistics", {})
            
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            
            # Calculate engagement rate
            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
            
            return AnalyticsData(
                views=views,
                likes=likes,
                comments=comments,
                engagement_rate=round(engagement_rate, 2),
                metadata={
                    "favorite_count": int(stats.get("favoriteCount", 0)),
                },
            )
            
        except Exception as e:
            logger.exception("YouTube analytics fetch error")
            return None
    
    async def get_account_analytics(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Get account-level analytics from YouTube Analytics API."""
        try:
            # YouTube Analytics API endpoint
            analytics_url = "https://youtubeanalytics.googleapis.com/v2/reports"
            
            response = await self.client.get(
                analytics_url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "ids": "channel==MINE",
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                    "metrics": "views,likes,comments,shares,subscribersGained,subscribersLost,estimatedMinutesWatched,averageViewDuration",
                    "dimensions": "day",
                    "sort": "day",
                },
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube account analytics failed: {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            logger.exception("YouTube account analytics error")
            return None

