"""
API Logging Service

Handles logging of all external API requests for debugging and monitoring.
Logs are stored in both the database (for searching) and application logs.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.api_request_log import (
    APIRequestLog,
    mask_sensitive_data,
    truncate_response,
    mask_api_key,
)

logger = logging.getLogger(__name__)


class APILoggingService:
    """
    Service for logging API requests to external providers.
    
    Features:
    - Logs to both database and application logs
    - Masks sensitive data (API keys, tokens)
    - Truncates large response bodies
    - Provides search and filtering capabilities
    """
    
    # Maximum response body size to store (in characters)
    MAX_RESPONSE_SIZE = 50000
    
    # Log retention period (days)
    RETENTION_DAYS = 30
    
    def __init__(self, db: Session):
        """
        Initialize the service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def log_request(
        self,
        provider: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_body: Optional[Dict[str, Any]] = None,
        duration_ms: int = 0,
        request_body: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        video_id: Optional[UUID] = None,
        generation_step: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> APIRequestLog:
        """
        Log an API request to the database.
        
        Args:
            provider: Provider name (e.g., 'openai_gpt', 'elevenlabs')
            endpoint: API endpoint URL
            method: HTTP method
            status_code: Response status code
            response_body: Response payload (will be truncated)
            duration_ms: Request duration in milliseconds
            request_body: Request payload (sensitive data will be masked)
            user_id: User who initiated the request
            video_id: Video being generated
            generation_step: Pipeline step (script, voice, etc.)
            error_message: Error message if failed
            error_details: Additional error context
            
        Returns:
            Created APIRequestLog record
        """
        # Mask sensitive data in request body
        masked_request = None
        if request_body:
            masked_request = mask_sensitive_data(request_body)
        
        # Truncate large response bodies
        truncated_response = None
        if response_body:
            truncated_response = truncate_response(response_body, self.MAX_RESPONSE_SIZE)
        
        # Create log record
        log = APIRequestLog(
            user_id=user_id,
            video_id=video_id,
            provider=provider,
            endpoint=endpoint,
            method=method,
            request_body=masked_request,
            status_code=status_code,
            response_body=truncated_response,
            duration_ms=duration_ms,
            error_message=error_message,
            error_details=error_details,
            generation_step=generation_step,
            created_at=datetime.utcnow(),
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        # Also log to application logs
        self._log_to_app_logger(log)
        
        return log
    
    def _log_to_app_logger(self, log: APIRequestLog) -> None:
        """
        Log the request to application logger.
        
        Args:
            log: APIRequestLog record
        """
        log_data = {
            "provider": log.provider,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "duration_ms": log.duration_ms,
            "user_id": str(log.user_id) if log.user_id else None,
            "video_id": str(log.video_id) if log.video_id else None,
            "generation_step": log.generation_step,
        }
        
        if log.is_error:
            logger.error(
                f"API request failed: {log.provider} {log.endpoint}",
                extra={
                    "api_log": log_data,
                    "error": log.error_message,
                }
            )
        else:
            logger.info(
                f"API request: {log.provider} {log.method} {log.status_code} ({log.duration_ms}ms)",
                extra={"api_log": log_data}
            )
    
    def get_logs(
        self,
        user_id: Optional[UUID] = None,
        video_id: Optional[UUID] = None,
        provider: Optional[str] = None,
        generation_step: Optional[str] = None,
        status_code: Optional[int] = None,
        is_error: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[APIRequestLog]:
        """
        Search and filter API logs.
        
        Args:
            user_id: Filter by user
            video_id: Filter by video
            provider: Filter by provider
            generation_step: Filter by generation step
            status_code: Filter by status code
            is_error: Filter by error status
            start_date: Filter by date range start
            end_date: Filter by date range end
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of APIRequestLog records
        """
        query = self.db.query(APIRequestLog)
        
        # Apply filters
        if user_id:
            query = query.filter(APIRequestLog.user_id == user_id)
        
        if video_id:
            query = query.filter(APIRequestLog.video_id == video_id)
        
        if provider:
            query = query.filter(APIRequestLog.provider == provider)
        
        if generation_step:
            query = query.filter(APIRequestLog.generation_step == generation_step)
        
        if status_code:
            query = query.filter(APIRequestLog.status_code == status_code)
        
        if is_error is not None:
            if is_error:
                query = query.filter(
                    (APIRequestLog.error_message.isnot(None)) |
                    (APIRequestLog.status_code >= 400)
                )
            else:
                query = query.filter(
                    APIRequestLog.error_message.is_(None),
                    APIRequestLog.status_code < 400
                )
        
        if start_date:
            query = query.filter(APIRequestLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(APIRequestLog.created_at <= end_date)
        
        # Order by most recent first
        query = query.order_by(desc(APIRequestLog.created_at))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_log_by_id(self, log_id: UUID) -> Optional[APIRequestLog]:
        """
        Get a specific log by ID.
        
        Args:
            log_id: Log record ID
            
        Returns:
            APIRequestLog or None
        """
        return self.db.query(APIRequestLog).filter(
            APIRequestLog.id == log_id
        ).first()
    
    def get_logs_for_video(self, video_id: UUID) -> List[APIRequestLog]:
        """
        Get all logs for a video generation.
        
        Args:
            video_id: Video ID
            
        Returns:
            List of APIRequestLog records ordered by creation time
        """
        return self.db.query(APIRequestLog).filter(
            APIRequestLog.video_id == video_id
        ).order_by(APIRequestLog.created_at).all()
    
    def get_error_logs(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[APIRequestLog]:
        """
        Get recent error logs.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum results
            
        Returns:
            List of error logs
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(APIRequestLog).filter(
            and_(
                APIRequestLog.created_at >= since,
                (APIRequestLog.error_message.isnot(None)) |
                (APIRequestLog.status_code >= 400)
            )
        ).order_by(desc(APIRequestLog.created_at)).limit(limit).all()
    
    def get_provider_stats(
        self,
        provider: str,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get statistics for a provider.
        
        Args:
            provider: Provider name
            hours: Time period to analyze
            
        Returns:
            Statistics dictionary
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        logs = self.db.query(APIRequestLog).filter(
            and_(
                APIRequestLog.provider == provider,
                APIRequestLog.created_at >= since,
            )
        ).all()
        
        if not logs:
            return {
                "provider": provider,
                "period_hours": hours,
                "total_requests": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_duration_ms": 0,
                "error_rate": 0,
            }
        
        success_count = sum(1 for log in logs if log.is_success)
        error_count = sum(1 for log in logs if log.is_error)
        total_duration = sum(log.duration_ms or 0 for log in logs)
        
        return {
            "provider": provider,
            "period_hours": hours,
            "total_requests": len(logs),
            "success_count": success_count,
            "error_count": error_count,
            "avg_duration_ms": total_duration // len(logs) if logs else 0,
            "error_rate": error_count / len(logs) if logs else 0,
        }
    
    def cleanup_old_logs(self, days: int = None) -> int:
        """
        Delete logs older than retention period.
        
        Args:
            days: Number of days to retain (uses default if not specified)
            
        Returns:
            Number of logs deleted
        """
        if days is None:
            days = self.RETENTION_DAYS
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        count = self.db.query(APIRequestLog).filter(
            APIRequestLog.created_at < cutoff
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {count} API logs older than {days} days")
        return count


# =============================================================================
# Logging Decorator
# =============================================================================

def log_api_request(
    provider: str,
    step: Optional[str] = None,
):
    """
    Decorator to automatically log API requests.
    
    Usage:
        @log_api_request("openai_gpt", "script")
        async def call_openai_api(self, ...):
            ...
    
    Args:
        provider: Provider name
        step: Generation step name
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            
            # Get db session from self if available
            db = getattr(self, 'db', None)
            config = getattr(self, 'config', None)
            
            user_id = config.user_id if config else None
            video_id = config.video_id if config else None
            
            try:
                result = await func(self, *args, **kwargs)
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log success if db available
                if db:
                    service = APILoggingService(db)
                    service.log_request(
                        provider=provider,
                        endpoint=getattr(self, '_last_endpoint', 'unknown'),
                        method=getattr(self, '_last_method', 'POST'),
                        status_code=getattr(self, '_last_status_code', 200),
                        response_body=getattr(self, '_last_response', None),
                        duration_ms=duration_ms,
                        user_id=user_id,
                        video_id=video_id,
                        generation_step=step,
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log error if db available
                if db:
                    service = APILoggingService(db)
                    service.log_request(
                        provider=provider,
                        endpoint=getattr(self, '_last_endpoint', 'unknown'),
                        method=getattr(self, '_last_method', 'POST'),
                        status_code=getattr(self, '_last_status_code', 500),
                        duration_ms=duration_ms,
                        user_id=user_id,
                        video_id=video_id,
                        generation_step=step,
                        error_message=str(e),
                        error_details={"exception_type": type(e).__name__},
                    )
                
                raise
        
        return wrapper
    return decorator
