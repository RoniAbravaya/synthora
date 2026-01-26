# Storage Service Module
# =====================
# Provides cloud storage functionality for uploading generated videos and media.
# Supports Google Cloud Storage with local file fallback for development.

from .gcs import GCSStorageService, get_storage_service

__all__ = ["GCSStorageService", "get_storage_service"]
