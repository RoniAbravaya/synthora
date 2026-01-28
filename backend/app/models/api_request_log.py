"""
API Request Log Model

Stores logs of all external API requests made during video generation.
Used for debugging, monitoring, and troubleshooting.

Features:
- Full request/response logging (with sensitive data masked)
- Duration tracking
- Error capture
- Searchable by user, video, provider, and time range
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

import uuid as uuid_lib
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class APIRequestLog(Base):
    """
    API request log for external service calls.
    
    This model stores information about every external API request made
    during video generation, including:
    - Request details (provider, endpoint, method)
    - Response details (status code, body, duration)
    - Error information if the request failed
    - Context (user, video, generation step)
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: User who initiated the request (nullable for system calls)
        video_id: Video being generated (nullable for validation calls)
        provider: Integration provider name
        endpoint: API endpoint URL
        method: HTTP method
        request_body: Request payload (sensitive data masked)
        status_code: HTTP response status code
        response_body: Response payload (may be truncated)
        duration_ms: Request duration in milliseconds
        error_message: Error message if request failed
        error_details: Additional error details
        generation_step: Video generation step (script, voice, etc.)
        created_at: Timestamp of the request
    
    Relationships:
        user: The user who initiated the request
        video: The video being generated
    """
    
    __tablename__ = "api_request_logs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    
    # Foreign Keys (nullable for flexibility)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who initiated the request"
    )
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Video being generated (if applicable)"
    )
    
    # Request information
    provider = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Integration provider name (e.g., openai_gpt, elevenlabs)"
    )
    endpoint = Column(
        String(500),
        nullable=False,
        doc="API endpoint URL"
    )
    method = Column(
        String(10),
        nullable=False,
        doc="HTTP method (GET, POST, etc.)"
    )
    request_body = Column(
        JSONB,
        nullable=True,
        doc="Request payload (sensitive data masked)"
    )
    
    # Response information
    status_code = Column(
        Integer,
        nullable=True,
        index=True,
        doc="HTTP response status code"
    )
    response_body = Column(
        JSONB,
        nullable=True,
        doc="Response payload (may be truncated for large responses)"
    )
    duration_ms = Column(
        Integer,
        nullable=True,
        doc="Request duration in milliseconds"
    )
    
    # Error information
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if request failed"
    )
    error_details = Column(
        JSONB,
        nullable=True,
        doc="Additional error details (stack trace, API error response, etc.)"
    )
    
    # Context
    generation_step = Column(
        String(50),
        nullable=True,
        doc="Video generation step (script, voice, media, video_ai, assembly)"
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="Timestamp of the request"
    )
    
    # Relationships
    user = relationship("User", backref="api_request_logs")
    video = relationship("Video", backref="api_request_logs")
    
    def __repr__(self) -> str:
        return f"<APIRequestLog(id={self.id}, provider={self.provider}, status={self.status_code})>"
    
    @property
    def is_success(self) -> bool:
        """Check if the request was successful (2xx status code)."""
        return self.status_code is not None and 200 <= self.status_code < 300
    
    @property
    def is_error(self) -> bool:
        """Check if the request resulted in an error."""
        return self.error_message is not None or (
            self.status_code is not None and self.status_code >= 400
        )
    
    def to_response(self) -> Dict[str, Any]:
        """Convert to response format for API."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "video_id": str(self.video_id) if self.video_id else None,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "is_success": self.is_success,
            "is_error": self.is_error,
            "error_message": self.error_message,
            "generation_step": self.generation_step,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_detailed_response(self) -> Dict[str, Any]:
        """Convert to detailed response format (includes request/response bodies)."""
        response = self.to_response()
        response.update({
            "request_body": self.request_body,
            "response_body": self.response_body,
            "error_details": self.error_details,
        })
        return response


# =============================================================================
# Utility functions for log creation
# =============================================================================

def mask_api_key(value: str) -> str:
    """
    Mask an API key to show only the last 4 characters.
    
    Args:
        value: The API key to mask
        
    Returns:
        Masked string like "****abcd"
    """
    if not value or len(value) < 4:
        return "****"
    return f"****{value[-4:]}"


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    """
    Recursively mask sensitive data in a dictionary.
    
    Args:
        data: Dictionary to mask
        sensitive_keys: List of keys to mask (default: common API key field names)
        
    Returns:
        Dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key", "apikey", "api-key",
            "authorization", "auth",
            "token", "access_token", "refresh_token",
            "secret", "password", "key",
            "x-api-key", "bearer",
        ]
    
    if not isinstance(data, dict):
        return data
    
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if this key should be masked
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str):
                masked[key] = mask_api_key(value)
            else:
                masked[key] = "****"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        elif isinstance(value, list):
            masked[key] = [
                mask_sensitive_data(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    
    return masked


def truncate_response(data: Any, max_length: int = 10000) -> Any:
    """
    Truncate large response data to avoid storing excessive data.
    
    Args:
        data: Response data to truncate
        max_length: Maximum length for string values
        
    Returns:
        Truncated data
    """
    if isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + f"... [truncated, total length: {len(data)}]"
    elif isinstance(data, dict):
        return {k: truncate_response(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > 100:
            return data[:100] + [f"... [truncated, total items: {len(data)}]"]
        return [truncate_response(item, max_length) for item in data]
    return data
