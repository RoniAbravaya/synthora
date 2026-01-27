"""
Authentication Core Module

Provides authentication dependencies for FastAPI routes.
Handles token extraction, verification, and user retrieval.
"""

import logging
from typing import Optional, List, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.firebase import verify_id_token, TokenVerificationError, UserInfo
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
# This tells FastAPI/OpenAPI that we expect a Bearer token in the Authorization header
bearer_scheme = HTTPBearer(
    scheme_name="Firebase",
    description="Firebase ID token (obtained from Firebase Auth)",
    auto_error=False,  # Don't auto-raise, we'll handle it ourselves
)


class AuthenticationError(HTTPException):
    """Authentication failed exception."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization failed exception (authenticated but not allowed)."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """
    Extract the Bearer token from the Authorization header.
    
    Args:
        credentials: HTTP authorization credentials from FastAPI
        
    Returns:
        The token string, or None if not provided
    """
    if credentials is None:
        return None
    return credentials.credentials


async def get_firebase_user_info(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[UserInfo]:
    """
    Verify the Firebase token and return user info.
    
    This dependency does NOT raise an error if no token is provided.
    Use this for optional authentication.
    
    Args:
        token: Firebase ID token from Authorization header
        
    Returns:
        UserInfo if token is valid, None otherwise
    """
    if not token:
        return None
    
    try:
        return verify_id_token(token)
    except TokenVerificationError as e:
        logger.warning(f"Token verification failed: {e.message}")
        return None


async def require_firebase_user_info(
    token: Optional[str] = Depends(get_token_from_header),
) -> UserInfo:
    """
    Verify the Firebase token and return user info.
    
    This dependency REQUIRES a valid token and raises an error if not provided.
    
    Args:
        token: Firebase ID token from Authorization header
        
    Returns:
        UserInfo from verified token
        
    Raises:
        AuthenticationError: If token is missing or invalid
    """
    if not token:
        raise AuthenticationError("Authorization header required")
    
    try:
        return verify_id_token(token)
    except TokenVerificationError as e:
        raise AuthenticationError(f"Invalid token: {e.message}")


async def get_current_user(
    firebase_user: UserInfo = Depends(require_firebase_user_info),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from the database.
    
    This dependency verifies the Firebase token and retrieves the
    corresponding user from our database.
    
    Args:
        firebase_user: Verified Firebase user info
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        AuthenticationError: If user not found in database
        
    Usage:
        ```python
        @router.get("/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            return {"email": user.email}
        ```
    """
    # Look up user by Firebase UID
    user = db.query(User).filter(User.firebase_uid == firebase_user.uid).first()
    
    if not user:
        # User exists in Firebase but not in our database
        # This shouldn't happen in normal flow (login creates the user)
        logger.warning(f"User not found in database: {firebase_user.uid}")
        raise AuthenticationError("User not found. Please log in again.")
    
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get the current authenticated user and verify they are active.
    
    Args:
        user: Current user from database
        
    Returns:
        User model instance (if active)
        
    Raises:
        AuthorizationError: If user account is disabled
    """
    if not user.is_active:
        raise AuthorizationError("Account is disabled")
    
    return user


async def get_optional_user(
    firebase_user: Optional[UserInfo] = Depends(get_firebase_user_info),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.
    
    Use this for endpoints that work both with and without authentication.
    
    Args:
        firebase_user: Optional Firebase user info
        db: Database session
        
    Returns:
        User model instance if authenticated, None otherwise
    """
    if not firebase_user:
        return None
    
    user = db.query(User).filter(User.firebase_uid == firebase_user.uid).first()
    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory that requires the user to have one of the specified roles.
    
    Args:
        *allowed_roles: Roles that are allowed to access the endpoint
        
    Returns:
        A dependency function that checks the user's role
        
    Usage:
        ```python
        @router.get("/admin/users")
        async def list_users(user: User = Depends(require_role(UserRole.ADMIN))):
            # Only admins can access this
            ...
        
        @router.get("/premium/feature")
        async def premium_feature(
            user: User = Depends(require_role(UserRole.ADMIN, UserRole.PREMIUM))
        ):
            # Admins and premium users can access this
            ...
        ```
    """
    async def role_checker(user: User = Depends(get_current_active_user)) -> User:
        # Handle both string and enum role values
        user_role = user.role if isinstance(user.role, str) else user.role.value
        allowed_role_values = [r.value for r in allowed_roles]
        if user_role not in allowed_role_values:
            raise AuthorizationError(
                f"This action requires one of these roles: {', '.join(allowed_role_values)}"
            )
        return user
    
    return role_checker


def require_admin(user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires the user to be an admin.
    
    Shorthand for `require_role(UserRole.ADMIN)`.
    
    Args:
        user: Current active user
        
    Returns:
        User model instance (if admin)
        
    Raises:
        AuthorizationError: If user is not an admin
    """
    # Handle both string and enum role values
    user_role = user.role if isinstance(user.role, str) else user.role.value
    if user_role != UserRole.ADMIN.value:
        raise AuthorizationError("Admin access required")
    return user


def require_premium(user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires the user to have premium access.
    
    Premium access includes both ADMIN and PREMIUM roles.
    
    Args:
        user: Current active user
        
    Returns:
        User model instance (if premium)
        
    Raises:
        AuthorizationError: If user doesn't have premium access
    """
    if not user.is_premium:
        raise AuthorizationError(
            "This feature requires a Premium subscription. "
            "Upgrade to unlock all features."
        )
    return user


# Convenience aliases for common use cases
AdminUser = Depends(require_admin)
PremiumUser = Depends(require_premium)
CurrentUser = Depends(get_current_active_user)
OptionalUser = Depends(get_optional_user)

