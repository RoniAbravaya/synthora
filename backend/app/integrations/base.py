"""
Base Integration Validator

Provides the abstract base class for all integration validators.
Each integration must implement the validate() method.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of an API key validation.
    
    Attributes:
        valid: Whether the API key is valid
        message: Human-readable status message
        details: Additional details (account info, quota, etc.)
        error_code: Error code if validation failed
    """
    valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "message": self.message,
            "details": self.details,
            "error_code": self.error_code,
        }


class BaseValidator(ABC):
    """
    Abstract base class for integration validators.
    
    Each integration provider should have a validator that inherits from this class
    and implements the validate() method.
    
    Attributes:
        provider_name: Display name of the provider
        timeout: Request timeout in seconds
    """
    
    provider_name: str = "Unknown Provider"
    timeout: int = 10
    
    def __init__(self, api_key: str):
        """
        Initialize the validator.
        
        Args:
            api_key: The API key to validate
        """
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def validate(self) -> ValidationResult:
        """
        Validate the API key.
        
        This method should make a test request to the provider's API
        to verify the API key is valid.
        
        Returns:
            ValidationResult with validation status and details
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _success(
        self,
        message: str = "API key is valid",
        details: Dict[str, Any] = None
    ) -> ValidationResult:
        """Create a successful validation result."""
        return ValidationResult(
            valid=True,
            message=message,
            details=details,
        )
    
    def _failure(
        self,
        message: str,
        error_code: str = "validation_failed",
        details: Dict[str, Any] = None
    ) -> ValidationResult:
        """Create a failed validation result."""
        return ValidationResult(
            valid=False,
            message=message,
            error_code=error_code,
            details=details,
        )
    
    def _handle_http_error(self, status_code: int, response_text: str) -> ValidationResult:
        """
        Handle common HTTP error codes.
        
        Args:
            status_code: HTTP status code
            response_text: Response body text
            
        Returns:
            ValidationResult with appropriate error message
        """
        if status_code == 401:
            return self._failure(
                "Invalid API key",
                error_code="invalid_key",
            )
        elif status_code == 403:
            return self._failure(
                "API key doesn't have required permissions",
                error_code="insufficient_permissions",
            )
        elif status_code == 429:
            return self._failure(
                "Rate limit exceeded. Try again later.",
                error_code="rate_limited",
            )
        elif status_code >= 500:
            return self._failure(
                f"{self.provider_name} service is temporarily unavailable",
                error_code="service_unavailable",
            )
        else:
            return self._failure(
                f"Validation failed with status {status_code}",
                error_code="unknown_error",
                details={"response": response_text[:200]},
            )

