"""
Common Pydantic Schemas

Shared schemas used across multiple endpoints.
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

# Generic type for paginated responses
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode
        populate_by_name=True,
        use_enum_values=True,
    )


class TimestampSchema(BaseSchema):
    """Schema mixin for timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema mixin for ID field."""
    
    id: UUID


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Number of records to return")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response."""
    
    items: List[T]
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items per page")
    
    @property
    def has_more(self) -> bool:
        """Check if there are more items."""
        return self.skip + len(self.items) < self.total
    
    @property
    def page(self) -> int:
        """Get current page number (1-indexed)."""
        if self.limit == 0:
            return 1
        return (self.skip // self.limit) + 1
    
    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        if self.limit == 0:
            return 1
        return (self.total + self.limit - 1) // self.limit


class ErrorDetail(BaseModel):
    """Error detail for validation errors."""
    
    field: str = Field(description="Field that caused the error")
    message: str = Field(description="Error message")
    type: str = Field(description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str = Field(description="Error message")
    errors: Optional[List[ErrorDetail]] = Field(default=None, description="Validation errors")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    message: str = Field(description="Success message")
    data: Optional[Any] = Field(default=None, description="Additional data")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(description="Health status")
    service: str = Field(description="Service name")
    checks: Optional[dict] = Field(default=None, description="Individual health checks")


class MessageResponse(BaseModel):
    """Simple message response."""
    
    message: str

