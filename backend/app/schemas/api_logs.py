"""
API Logs Schemas

Pydantic schemas for API logs admin endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class APILogResponse(BaseModel):
    """Response for a single API log entry."""
    id: str
    user_id: Optional[str]
    video_id: Optional[str]
    provider: str
    endpoint: str
    method: str
    status_code: Optional[int]
    duration_ms: Optional[int]
    is_success: bool
    is_error: bool
    error_message: Optional[str]
    generation_step: Optional[str]
    created_at: str


class APILogDetailResponse(APILogResponse):
    """Detailed response including request/response bodies."""
    request_body: Optional[Dict[str, Any]]
    response_body: Optional[Dict[str, Any]]
    error_details: Optional[Dict[str, Any]]


class APILogsListResponse(BaseModel):
    """Response for list of API logs."""
    logs: List[APILogResponse]
    total: int
    limit: int
    offset: int


class APILogsSearchParams(BaseModel):
    """Search parameters for API logs."""
    user_id: Optional[str] = None
    video_id: Optional[str] = None
    provider: Optional[str] = None
    generation_step: Optional[str] = None
    status_code: Optional[int] = None
    is_error: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class ProviderStatsResponse(BaseModel):
    """Statistics for a provider."""
    provider: str
    period_hours: int
    total_requests: int
    success_count: int
    error_count: int
    avg_duration_ms: int
    error_rate: float


class AllProviderStatsResponse(BaseModel):
    """Statistics for all providers."""
    stats: List[ProviderStatsResponse]
    period_hours: int
