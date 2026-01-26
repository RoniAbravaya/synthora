# Google Cloud Storage Service
# ============================
# Handles uploading files to Google Cloud Storage for generated videos.
# Falls back to local file URLs when GCS is not configured.

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GCSStorageService:
    """
    Service for uploading files to Google Cloud Storage.
    
    If GCS credentials are not configured, provides a warning and returns
    local file URLs (not suitable for production).
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._bucket = None
        self._initialized = False
        self._init_error: Optional[str] = None
        
    def _initialize(self) -> bool:
        """
        Lazy initialization of GCS client.
        
        Returns True if GCS is available, False otherwise.
        """
        if self._initialized:
            return self._client is not None
            
        self._initialized = True
        
        # Log current GCS configuration (without sensitive data)
        bucket_name = self.settings.GCS_BUCKET_NAME
        project_id = self.settings.GCS_PROJECT_ID
        has_json_creds = bool(self.settings.GCS_SERVICE_ACCOUNT_JSON)
        has_path_creds = bool(self.settings.GCS_SERVICE_ACCOUNT_PATH)
        
        logger.info(f"GCS Configuration: bucket={bucket_name}, project={project_id}, "
                   f"has_json_creds={has_json_creds}, has_path_creds={has_path_creds}")
        print(f"[GCS] Configuration: bucket={bucket_name}, project={project_id}, "
              f"has_json_creds={has_json_creds}, has_path_creds={has_path_creds}")
        
        # Check if GCS is configured
        if not self.settings.GCS_BUCKET_NAME:
            msg = ("GCS_BUCKET_NAME not configured. Videos will be saved locally "
                   "and will NOT persist across container restarts. "
                   "Configure GCS for production use.")
            logger.warning(msg)
            print(f"[GCS] WARNING: {msg}")
            self._init_error = "GCS_BUCKET_NAME not configured"
            return False
            
        try:
            from google.cloud import storage
            from google.oauth2 import service_account
            
            # Try to get credentials from JSON string first, then file path
            credentials = None
            
            if self.settings.GCS_SERVICE_ACCOUNT_JSON:
                # Parse JSON string from environment variable
                try:
                    creds_info = json.loads(self.settings.GCS_SERVICE_ACCOUNT_JSON)
                    credentials = service_account.Credentials.from_service_account_info(creds_info)
                    logger.info("Using GCS credentials from GCS_SERVICE_ACCOUNT_JSON")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GCS_SERVICE_ACCOUNT_JSON: {e}")
                    self._init_error = f"Invalid GCS_SERVICE_ACCOUNT_JSON: {e}"
                    return False
                    
            elif self.settings.GCS_SERVICE_ACCOUNT_PATH:
                # Load from file path
                path = Path(self.settings.GCS_SERVICE_ACCOUNT_PATH)
                if path.exists():
                    credentials = service_account.Credentials.from_service_account_file(str(path))
                    logger.info(f"Using GCS credentials from file: {path}")
                else:
                    logger.error(f"GCS service account file not found: {path}")
                    self._init_error = f"Service account file not found: {path}"
                    return False
            else:
                # Try default credentials (for GCP-hosted environments)
                logger.info("Using default GCS credentials (GOOGLE_APPLICATION_CREDENTIALS)")
                
            # Create client
            if credentials:
                self._client = storage.Client(
                    project=self.settings.GCS_PROJECT_ID,
                    credentials=credentials
                )
            else:
                self._client = storage.Client(project=self.settings.GCS_PROJECT_ID)
                
            # Get bucket
            self._bucket = self._client.bucket(self.settings.GCS_BUCKET_NAME)
            
            # Verify bucket exists
            if not self._bucket.exists():
                logger.error(f"GCS bucket does not exist: {self.settings.GCS_BUCKET_NAME}")
                self._init_error = f"Bucket not found: {self.settings.GCS_BUCKET_NAME}"
                self._client = None
                self._bucket = None
                return False
                
            logger.info(f"GCS initialized successfully. Bucket: {self.settings.GCS_BUCKET_NAME}")
            return True
            
        except ImportError as e:
            msg = f"google-cloud-storage package not installed: {e}"
            logger.error(msg)
            print(f"[GCS] ERROR: {msg}")
            self._init_error = "google-cloud-storage package not installed"
            return False
        except Exception as e:
            msg = f"Failed to initialize GCS: {e}"
            logger.error(msg)
            print(f"[GCS] ERROR: {msg}")
            self._init_error = str(e)
            return False
            
    def is_available(self) -> bool:
        """Check if GCS is available for uploads."""
        return self._initialize()
        
    def get_init_error(self) -> Optional[str]:
        """Get the initialization error if GCS is not available."""
        self._initialize()
        return self._init_error
    
    def upload_video(
        self,
        local_path: str,
        user_id: str,
        video_id: str,
        content_type: str = "video/mp4",
    ) -> Tuple[str, bool]:
        """
        Upload a video file to GCS.
        
        Args:
            local_path: Path to the local video file
            user_id: User ID for organizing files
            video_id: Video ID for unique filename
            content_type: MIME type of the file
            
        Returns:
            Tuple of (url, is_cloud_url) where is_cloud_url indicates if
            the URL is a proper cloud URL vs a local file path
        """
        logger.info(f"[GCS] upload_video called: local_path={local_path}, user_id={user_id}, video_id={video_id}")
        print(f"[GCS] upload_video called: local_path={local_path}, user_id={user_id}, video_id={video_id}")
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Video file not found: {local_path}")
            
        # Check if GCS is available
        if not self._initialize():
            msg = f"GCS not available ({self._init_error}). Returning local file URL for {local_path}"
            logger.warning(msg)
            print(f"[GCS] WARNING: {msg}")
            return f"file://{local_path}", False
            
        try:
            # Generate cloud storage path
            # Format: videos/{user_id}/{date}/{video_id}.mp4
            date_str = datetime.utcnow().strftime("%Y/%m/%d")
            extension = Path(local_path).suffix or ".mp4"
            blob_name = f"videos/{user_id}/{date_str}/{video_id}{extension}"
            
            # Upload to GCS
            blob = self._bucket.blob(blob_name)
            blob.upload_from_filename(local_path, content_type=content_type)
            
            # Make the blob publicly readable
            # In production, you might want to use signed URLs instead
            blob.make_public()
            
            public_url = blob.public_url
            logger.info(f"Video uploaded to GCS: {public_url}")
            
            return public_url, True
            
        except Exception as e:
            logger.error(f"Failed to upload video to GCS: {e}")
            # Fall back to local URL
            return f"file://{local_path}", False
            
    def upload_thumbnail(
        self,
        local_path: str,
        user_id: str,
        video_id: str,
        content_type: str = "image/jpeg",
    ) -> Tuple[str, bool]:
        """
        Upload a thumbnail image to GCS.
        
        Similar to upload_video but for thumbnails.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Thumbnail file not found: {local_path}")
            
        if not self._initialize():
            logger.warning(f"GCS not available. Returning local file URL for {local_path}")
            return f"file://{local_path}", False
            
        try:
            date_str = datetime.utcnow().strftime("%Y/%m/%d")
            extension = Path(local_path).suffix or ".jpg"
            blob_name = f"thumbnails/{user_id}/{date_str}/{video_id}{extension}"
            
            blob = self._bucket.blob(blob_name)
            blob.upload_from_filename(local_path, content_type=content_type)
            blob.make_public()
            
            public_url = blob.public_url
            logger.info(f"Thumbnail uploaded to GCS: {public_url}")
            
            return public_url, True
            
        except Exception as e:
            logger.error(f"Failed to upload thumbnail to GCS: {e}")
            return f"file://{local_path}", False
            
    def generate_signed_url(
        self,
        blob_name: str,
        expiration_hours: int = 24,
    ) -> Optional[str]:
        """
        Generate a signed URL for private blob access.
        
        Args:
            blob_name: The name/path of the blob in the bucket
            expiration_hours: Hours until the URL expires
            
        Returns:
            Signed URL string or None if GCS is not available
        """
        if not self._initialize():
            return None
            
        try:
            blob = self._bucket.blob(blob_name)
            url = blob.generate_signed_url(
                expiration=timedelta(hours=expiration_hours),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None
            
    def delete_video(self, video_url: str) -> bool:
        """
        Delete a video from GCS.
        
        Args:
            video_url: The public URL of the video
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._initialize():
            return False
            
        try:
            # Extract blob name from URL
            # URL format: https://storage.googleapis.com/{bucket}/{blob_name}
            bucket_url = f"https://storage.googleapis.com/{self.settings.GCS_BUCKET_NAME}/"
            if video_url.startswith(bucket_url):
                blob_name = video_url[len(bucket_url):]
                blob = self._bucket.blob(blob_name)
                blob.delete()
                logger.info(f"Deleted video from GCS: {blob_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete video from GCS: {e}")
            
        return False


@lru_cache()
def get_storage_service() -> GCSStorageService:
    """Get the singleton storage service instance."""
    return GCSStorageService()
