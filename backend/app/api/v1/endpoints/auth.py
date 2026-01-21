"""
Authentication API Endpoints

Handles user authentication via Firebase and session management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import (
    get_current_active_user,
    require_firebase_user_info,
    get_optional_user,
)
from app.services.firebase import (
    UserInfo,
    verify_id_token,
    TokenVerificationError,
    revoke_refresh_tokens,
)
from app.services.user import UserService, get_user_service
from app.models.user import User
from app.models.app_settings import AppSettings
from app.schemas.user import (
    FirebaseTokenRequest,
    LoginResponse,
    UserProfileResponse,
    SetupStatusResponse,
)
from app.schemas.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: FirebaseTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user with Firebase ID token.
    
    This endpoint:
    1. Verifies the Firebase ID token
    2. Creates a new user in our database if they don't exist
    3. Updates the user's last login time
    4. Returns the user profile with feature access info
    
    **Request Body:**
    - `id_token`: Firebase ID token obtained from Firebase Auth SDK
    
    **Returns:**
    - User profile with subscription and feature access information
    - `is_new_user`: Whether this is a first-time login
    - `setup_required`: Whether onboarding is needed
    
    **Errors:**
    - 401: Invalid or expired token
    """
    try:
        # Verify the Firebase token
        firebase_user = verify_id_token(request.id_token)
    except TokenVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create or update user in our database
    user_service = UserService(db)
    user, is_new_user = user_service.create_or_update_from_firebase(firebase_user)
    
    # Get profile data
    profile_data = user_service.get_user_profile_data(user)
    
    # Determine if onboarding is needed
    # New users need to set up integrations before they can generate videos
    setup_required = is_new_user or profile_data["integrations_configured"] < 4
    
    # Build response
    user_profile = UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        **profile_data,
    )
    
    return LoginResponse(
        user=user_profile,
        is_new_user=is_new_user,
        setup_required=setup_required,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: User = Depends(get_current_active_user),
):
    """
    Log out the current user.
    
    This endpoint revokes the user's Firebase refresh tokens,
    invalidating all their sessions across devices.
    
    **Requires:** Authentication
    
    **Note:** The client should also clear local tokens/storage.
    """
    # Revoke Firebase refresh tokens
    success = revoke_refresh_tokens(user.firebase_uid)
    
    if success:
        logger.info(f"User logged out: {user.email}")
        return MessageResponse(message="Successfully logged out")
    else:
        # Even if revocation fails, we consider logout successful
        # The client will clear local tokens anyway
        logger.warning(f"Failed to revoke tokens for user: {user.email}")
        return MessageResponse(message="Logged out (token revocation failed)")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user's profile.
    
    Returns comprehensive profile information including:
    - Basic user info (email, name, avatar)
    - Role and subscription status
    - Feature access flags
    - Usage statistics
    
    **Requires:** Authentication
    """
    user_service = UserService(db)
    profile_data = user_service.get_user_profile_data(user)
    
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        **profile_data,
    )


@router.get("/setup-status", response_model=SetupStatusResponse)
async def get_setup_status(
    db: Session = Depends(get_db),
):
    """
    Check if initial application setup is complete.
    
    This endpoint is used by the frontend to determine whether
    to show the setup wizard or the login page.
    
    **Returns:**
    - `setup_completed`: True if at least one admin exists
    - `message`: Human-readable status message
    
    **Note:** This endpoint does not require authentication.
    """
    user_service = UserService(db)
    
    # Check if any admin exists
    admin_exists = user_service.admin_exists()
    
    if admin_exists:
        return SetupStatusResponse(
            setup_completed=True,
            message="Application is ready. Please sign in.",
        )
    else:
        return SetupStatusResponse(
            setup_completed=False,
            message="Welcome! The first user to sign in will become the administrator.",
        )


@router.post("/verify-token", response_model=MessageResponse)
async def verify_token(
    request: FirebaseTokenRequest,
):
    """
    Verify a Firebase ID token without logging in.
    
    This endpoint can be used to check if a token is valid
    without creating/updating a user in the database.
    
    **Request Body:**
    - `id_token`: Firebase ID token to verify
    
    **Returns:**
    - Success message if token is valid
    
    **Errors:**
    - 401: Invalid or expired token
    """
    try:
        firebase_user = verify_id_token(request.id_token)
        return MessageResponse(
            message=f"Token valid for user: {firebase_user.email}"
        )
    except TokenVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=MessageResponse)
async def refresh_session(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Refresh the user's session.
    
    Updates the last_login_at timestamp and returns a success message.
    The actual token refresh is handled by Firebase on the client side.
    
    **Requires:** Authentication
    """
    from datetime import datetime
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(message="Session refreshed")
