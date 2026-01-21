"""
Synthora FastAPI Dependencies

This module provides dependency injection functions for FastAPI routes.
Dependencies handle common concerns like authentication, authorization,
rate limiting, and database access.

Usage:
    @router.get("/protected")
    async def protected_route(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        return {"user": current_user.email}
"""

from datetime import datetime
from typing import Optional
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

# Firebase Admin SDK will be initialized in firebase service
# from app.services.firebase import verify_firebase_token


# HTTP Bearer token scheme for Firebase JWT
security = HTTPBearer(auto_error=False)

settings = get_settings()


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


class InsufficientPermissions(HTTPException):
    """Exception raised when user doesn't have required permissions."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class NotAuthenticated(HTTPException):
    """Exception raised when user is not authenticated."""
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get the current user if authenticated, or None if not.
    
    This dependency is useful for routes that work differently
    for authenticated vs anonymous users.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User model instance or None
    """
    if not credentials:
        return None
    
    try:
        # Import here to avoid circular imports
        from app.services.firebase import verify_firebase_token
        from app.services.user import get_user_by_firebase_uid
        
        # Verify Firebase token
        decoded_token = verify_firebase_token(credentials.credentials)
        if not decoded_token:
            return None
        
        # Get user from database
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            return None
        
        user = get_user_by_firebase_uid(db, firebase_uid)
        return user
    except Exception:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get the current authenticated user.
    
    This dependency requires authentication and will raise an error
    if the user is not authenticated.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        NotAuthenticated: If no valid token is provided
        HTTPException: If user not found in database
    """
    if not credentials:
        raise NotAuthenticated()
    
    try:
        # Import here to avoid circular imports
        from app.services.firebase import verify_firebase_token
        from app.services.user import get_user_by_firebase_uid
        
        # Verify Firebase token
        decoded_token = verify_firebase_token(credentials.credentials)
        if not decoded_token:
            raise NotAuthenticated("Invalid or expired token")
        
        # Get user from database
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise NotAuthenticated("Invalid token: missing user ID")
        
        user = get_user_by_firebase_uid(db, firebase_uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please complete registration."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
    except NotAuthenticated:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise NotAuthenticated(f"Authentication failed: {str(e)}")


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    Get the current active user.
    
    This is an alias for get_current_user that explicitly checks
    the user is active (not disabled).
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model instance
    """
    # Active check is already done in get_current_user
    return current_user


def require_role(*allowed_roles: str):
    """
    Dependency factory that requires the user to have one of the specified roles.
    
    Args:
        *allowed_roles: Role names that are allowed (e.g., "admin", "premium")
        
    Returns:
        Dependency function that validates user role
        
    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
        
        @router.get("/premium-feature")
        async def premium_route(user = Depends(require_role("admin", "premium"))):
            return {"message": "Premium feature"}
    """
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise InsufficientPermissions(
                f"This action requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


def require_admin():
    """
    Dependency that requires admin role.
    
    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(user_id: str, admin = Depends(require_admin())):
            # Only admins can delete users
            pass
    """
    return require_role("admin")


def require_premium():
    """
    Dependency that requires premium or admin role.
    
    Usage:
        @router.get("/ai-suggestions")
        async def get_suggestions(user = Depends(require_premium())):
            # Only premium users and admins can access
            pass
    """
    return require_role("admin", "premium")


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    Note: For production with multiple workers, use Redis-based rate limiting.
    This is a basic implementation for development.
    
    Usage:
        rate_limiter = RateLimiter(requests_per_minute=100)
        
        @router.get("/api/resource")
        async def get_resource(
            request: Request,
            _: None = Depends(rate_limiter)
        ):
            return {"data": "..."}
    """
    
    def __init__(self, requests_per_minute: int = None):
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self._requests: dict = {}  # {user_id: [(timestamp, count)]}
    
    async def __call__(
        self,
        request: Request,
        current_user = Depends(get_current_user_optional)
    ):
        """
        Check if the request should be rate limited.
        
        Args:
            request: FastAPI request object
            current_user: Current user (optional)
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Use user ID if authenticated, otherwise use IP
        if current_user:
            identifier = str(current_user.id)
        else:
            identifier = request.client.host if request.client else "unknown"
        
        now = datetime.utcnow()
        minute_ago = now.timestamp() - 60
        
        # Clean old entries and count recent requests
        if identifier in self._requests:
            self._requests[identifier] = [
                (ts, count) for ts, count in self._requests[identifier]
                if ts > minute_ago
            ]
            recent_count = sum(count for _, count in self._requests[identifier])
        else:
            self._requests[identifier] = []
            recent_count = 0
        
        # Check limit
        if recent_count >= self.requests_per_minute:
            raise RateLimitExceeded(
                f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        
        # Record this request
        self._requests[identifier].append((now.timestamp(), 1))


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_video_generation_limit(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """
    Check if the user can generate a video based on their plan limits.
    
    Free users: 1 video per day
    Premium users: Unlimited
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        True if user can generate a video
        
    Raises:
        HTTPException: If daily limit is reached
    """
    # Import here to avoid circular imports
    from app.services.limits import check_daily_video_limit
    
    can_generate, message = check_daily_video_limit(db, current_user)
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )
    return True


async def check_concurrent_generation(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """
    Check if the user has a video currently being generated.
    
    Only 1 concurrent video generation is allowed per user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        True if no concurrent generation
        
    Raises:
        HTTPException: If a video is already being generated
    """
    # Import here to avoid circular imports
    from app.services.limits import check_concurrent_generation_limit
    
    can_generate, message = check_concurrent_generation_limit(db, current_user)
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message
        )
    return True


async def check_scheduling_access(
    current_user = Depends(get_current_user)
) -> bool:
    """
    Check if the user has access to scheduling features.
    
    Only premium users and admins can schedule posts.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        True if user can schedule
        
    Raises:
        HTTPException: If user doesn't have scheduling access
    """
    if current_user.role not in ("admin", "premium"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scheduling is a premium feature. Please upgrade your plan."
        )
    return True


async def check_ai_suggestions_access(
    current_user = Depends(get_current_user)
) -> bool:
    """
    Check if the user has access to AI suggestions.
    
    Only premium users and admins can access AI suggestions.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        True if user can access AI suggestions
        
    Raises:
        HTTPException: If user doesn't have AI suggestions access
    """
    if current_user.role not in ("admin", "premium"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI suggestions is a premium feature. Please upgrade your plan."
        )
    return True

