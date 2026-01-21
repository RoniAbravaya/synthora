"""
Firebase Service

Handles Firebase Admin SDK initialization and token verification.
This service is the bridge between Firebase Authentication and our backend.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import (
    InvalidIdTokenError,
    ExpiredIdTokenError,
    RevokedIdTokenError,
    UserNotFoundError,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global flag to track initialization
_firebase_initialized = False


def initialize_firebase() -> bool:
    """
    Initialize the Firebase Admin SDK.
    
    This function should be called once during application startup.
    It uses the service account credentials from environment variables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
        
    Note:
        The function is idempotent - calling it multiple times is safe.
        It will only initialize Firebase once.
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        logger.debug("Firebase already initialized")
        return True
    
    settings = get_settings()
    
    try:
        # Check if credentials are configured
        if not settings.FIREBASE_CREDENTIALS_PATH and not settings.FIREBASE_CREDENTIALS_JSON:
            logger.warning(
                "Firebase credentials not configured. "
                "Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON"
            )
            return False
        
        # Initialize with credentials file path
        if settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with credentials file")
        
        # Initialize with credentials JSON (for Railway/production)
        elif settings.FIREBASE_CREDENTIALS_JSON:
            import json
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with credentials JSON")
        
        _firebase_initialized = True
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False


def is_firebase_initialized() -> bool:
    """Check if Firebase has been initialized."""
    return _firebase_initialized


class FirebaseAuthError(Exception):
    """Base exception for Firebase authentication errors."""
    
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TokenVerificationError(FirebaseAuthError):
    """Raised when token verification fails."""
    pass


class UserInfo:
    """
    Represents verified user information from Firebase.
    
    Attributes:
        uid: Firebase user ID
        email: User's email address
        name: User's display name (optional)
        picture: User's profile picture URL (optional)
        email_verified: Whether the email is verified
        provider: Authentication provider (google.com, password, etc.)
    """
    
    def __init__(
        self,
        uid: str,
        email: str,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        email_verified: bool = False,
        provider: Optional[str] = None,
    ):
        self.uid = uid
        self.email = email
        self.name = name
        self.picture = picture
        self.email_verified = email_verified
        self.provider = provider
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uid": self.uid,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "email_verified": self.email_verified,
            "provider": self.provider,
        }
    
    def __repr__(self) -> str:
        return f"<UserInfo(uid={self.uid}, email={self.email})>"


def verify_id_token(id_token: str, check_revoked: bool = True) -> UserInfo:
    """
    Verify a Firebase ID token and extract user information.
    
    This function verifies the token signature, expiration, and optionally
    checks if the token has been revoked.
    
    Args:
        id_token: The Firebase ID token to verify
        check_revoked: Whether to check if the token has been revoked
        
    Returns:
        UserInfo: Verified user information
        
    Raises:
        TokenVerificationError: If the token is invalid, expired, or revoked
        
    Example:
        ```python
        try:
            user_info = verify_id_token(token)
            print(f"Verified user: {user_info.email}")
        except TokenVerificationError as e:
            print(f"Token invalid: {e.message}")
        ```
    """
    if not _firebase_initialized:
        raise TokenVerificationError(
            "Firebase not initialized",
            code="firebase_not_initialized"
        )
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token, check_revoked=check_revoked)
        
        # Extract user information
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        if not uid or not email:
            raise TokenVerificationError(
                "Token missing required claims (uid or email)",
                code="invalid_claims"
            )
        
        # Get additional user info
        name = decoded_token.get("name")
        picture = decoded_token.get("picture")
        email_verified = decoded_token.get("email_verified", False)
        
        # Determine the authentication provider
        provider = None
        firebase_info = decoded_token.get("firebase", {})
        sign_in_provider = firebase_info.get("sign_in_provider")
        if sign_in_provider:
            provider = sign_in_provider
        
        return UserInfo(
            uid=uid,
            email=email,
            name=name,
            picture=picture,
            email_verified=email_verified,
            provider=provider,
        )
        
    except InvalidIdTokenError as e:
        logger.warning(f"Invalid ID token: {e}")
        raise TokenVerificationError(
            "Invalid ID token",
            code="invalid_token"
        )
    
    except ExpiredIdTokenError as e:
        logger.warning(f"Expired ID token: {e}")
        raise TokenVerificationError(
            "ID token has expired",
            code="token_expired"
        )
    
    except RevokedIdTokenError as e:
        logger.warning(f"Revoked ID token: {e}")
        raise TokenVerificationError(
            "ID token has been revoked",
            code="token_revoked"
        )
    
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise TokenVerificationError(
            f"Token verification failed: {str(e)}",
            code="verification_failed"
        )


def get_firebase_user(uid: str) -> Optional[Dict[str, Any]]:
    """
    Get user information directly from Firebase by UID.
    
    This can be used to get fresh user data or verify a user exists.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        Dict with user information, or None if user not found
    """
    if not _firebase_initialized:
        logger.warning("Firebase not initialized")
        return None
    
    try:
        user = auth.get_user(uid)
        return {
            "uid": user.uid,
            "email": user.email,
            "name": user.display_name,
            "picture": user.photo_url,
            "email_verified": user.email_verified,
            "disabled": user.disabled,
            "created_at": user.user_metadata.creation_timestamp,
            "last_sign_in": user.user_metadata.last_sign_in_timestamp,
        }
    except UserNotFoundError:
        logger.warning(f"Firebase user not found: {uid}")
        return None
    except Exception as e:
        logger.error(f"Error fetching Firebase user: {e}")
        return None


def revoke_refresh_tokens(uid: str) -> bool:
    """
    Revoke all refresh tokens for a user.
    
    This will invalidate all existing sessions for the user,
    forcing them to re-authenticate.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not _firebase_initialized:
        logger.warning("Firebase not initialized")
        return False
    
    try:
        auth.revoke_refresh_tokens(uid)
        logger.info(f"Revoked refresh tokens for user: {uid}")
        return True
    except Exception as e:
        logger.error(f"Failed to revoke refresh tokens: {e}")
        return False


def set_custom_claims(uid: str, claims: Dict[str, Any]) -> bool:
    """
    Set custom claims on a Firebase user.
    
    Custom claims can be used to store role information or other
    metadata that will be included in the ID token.
    
    Args:
        uid: Firebase user ID
        claims: Dictionary of custom claims
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        ```python
        set_custom_claims(uid, {"admin": True, "role": "premium"})
        ```
    """
    if not _firebase_initialized:
        logger.warning("Firebase not initialized")
        return False
    
    try:
        auth.set_custom_user_claims(uid, claims)
        logger.info(f"Set custom claims for user {uid}: {claims}")
        return True
    except Exception as e:
        logger.error(f"Failed to set custom claims: {e}")
        return False

