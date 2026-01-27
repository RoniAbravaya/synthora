"""
Social OAuth Service

Manages OAuth flows and token storage for social media platforms.
"""

import logging
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount, SocialPlatform, AccountStatus
from app.core.security import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


class SocialOAuthService:
    """
    Service class for managing social media OAuth flows.
    
    Handles:
    - OAuth state generation and validation
    - Token storage (encrypted)
    - Token refresh
    - Account connection management
    """
    
    # Token expiry buffer (refresh tokens before they expire)
    TOKEN_REFRESH_BUFFER = timedelta(minutes=5)
    
    def __init__(self, db: Session):
        """
        Initialize the OAuth service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._state_store: Dict[str, Dict[str, Any]] = {}  # In production, use Redis
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def generate_oauth_state(
        self,
        user_id: UUID,
        platform: SocialPlatform,
        redirect_uri: str,
    ) -> str:
        """
        Generate a secure OAuth state parameter.
        
        Args:
            user_id: User's UUID
            platform: Social platform
            redirect_uri: Callback URI after OAuth
            
        Returns:
            State string to include in OAuth request
        """
        state = secrets.token_urlsafe(32)
        
        # Store state with metadata (in production, use Redis with TTL)
        self._state_store[state] = {
            "user_id": str(user_id),
            "platform": platform.value,
            "redirect_uri": redirect_uri,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"Generated OAuth state for user {user_id}, platform {platform.value}")
        return state
    
    def validate_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Validate an OAuth state parameter.
        
        Args:
            state: State string from OAuth callback
            
        Returns:
            State metadata if valid, None otherwise
        """
        state_data = self._state_store.pop(state, None)
        
        if not state_data:
            logger.warning(f"Invalid OAuth state: {state}")
            return None
        
        # Check if state is expired (15 minutes)
        created_at = datetime.fromisoformat(state_data["created_at"])
        if datetime.utcnow() - created_at > timedelta(minutes=15):
            logger.warning(f"Expired OAuth state: {state}")
            return None
        
        return state_data
    
    # =========================================================================
    # Account Management
    # =========================================================================
    
    def get_user_accounts(
        self,
        user_id: UUID,
        platform: Optional[SocialPlatform] = None,
    ) -> List[SocialAccount]:
        """
        Get all social accounts for a user.
        
        Args:
            user_id: User's UUID
            platform: Optional platform filter
            
        Returns:
            List of SocialAccount instances
        """
        query = self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id
        )
        
        if platform:
            # Handle both enum and string values
            platform_value = platform.value if hasattr(platform, 'value') else platform
            query = query.filter(SocialAccount.platform == platform_value)
        
        return query.order_by(SocialAccount.created_at.desc()).all()
    
    def get_account_by_id(self, account_id: UUID) -> Optional[SocialAccount]:
        """Get a social account by ID."""
        return self.db.query(SocialAccount).filter(
            SocialAccount.id == account_id
        ).first()
    
    def get_account_by_platform_id(
        self,
        user_id: UUID,
        platform: SocialPlatform,
        platform_user_id: str,
    ) -> Optional[SocialAccount]:
        """
        Get a social account by platform user ID.
        
        Args:
            user_id: User's UUID
            platform: Social platform
            platform_user_id: Platform-specific user ID
            
        Returns:
            SocialAccount if found
        """
        # Handle both enum and string values
        platform_value = platform.value if hasattr(platform, 'value') else platform
        return self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform_value,
            SocialAccount.platform_user_id == platform_user_id,
        ).first()
    
    def create_or_update_account(
        self,
        user_id: UUID,
        platform: SocialPlatform,
        platform_user_id: str,
        username: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        profile_url: Optional[str] = None,
        avatar_url: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SocialAccount:
        """
        Create or update a social account after OAuth.
        
        Args:
            user_id: User's UUID
            platform: Social platform
            platform_user_id: Platform-specific user ID
            username: Display name on platform
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            token_expires_at: Token expiration time
            profile_url: Link to profile
            avatar_url: Profile picture URL
            scopes: Granted OAuth scopes
            metadata: Additional platform-specific data
            
        Returns:
            Created or updated SocialAccount instance
        """
        # Check for existing account
        account = self.get_account_by_platform_id(user_id, platform, platform_user_id)
        
        # Encrypt tokens
        encrypted_access = encrypt_value(access_token)
        encrypted_refresh = encrypt_value(refresh_token) if refresh_token else None
        
        # Convert platform enum to string value
        platform_str = platform.value if hasattr(platform, 'value') else platform
        
        if account:
            # Update existing account
            account.username = username
            account.access_token_encrypted = encrypted_access
            account.refresh_token_encrypted = encrypted_refresh
            account.token_expires_at = token_expires_at
            account.profile_url = profile_url
            account.avatar_url = avatar_url
            account.scopes = scopes or []
            account.extra_metadata = metadata or {}
            account.status = "connected"
            account.is_active = True
            account.last_used_at = datetime.utcnow()
            
            logger.info(f"Updated social account: {platform_str}/{username}")
        else:
            # Create new account
            account = SocialAccount(
                user_id=user_id,
                platform=platform_str,
                platform_user_id=platform_user_id,
                username=username,
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                token_expires_at=token_expires_at,
                profile_url=profile_url,
                avatar_url=avatar_url,
                scopes=scopes or [],
                extra_metadata=metadata or {},
                status="connected",
                is_active=True,
            )
            self.db.add(account)
            
            logger.info(f"Created social account: {platform_str}/{username}")
        
        self.db.commit()
        self.db.refresh(account)
        
        return account
    
    def disconnect_account(self, account: SocialAccount) -> None:
        """
        Disconnect a social account.
        
        Args:
            account: SocialAccount to disconnect
        """
        account_info = f"{account.platform}/{account.username}"
        
        self.db.delete(account)
        self.db.commit()
        
        logger.info(f"Disconnected social account: {account_info}")
    
    # =========================================================================
    # Token Management
    # =========================================================================
    
    def get_access_token(self, account: SocialAccount) -> Optional[str]:
        """
        Get the decrypted access token for an account.
        
        Automatically refreshes if expired.
        
        Args:
            account: SocialAccount instance
            
        Returns:
            Access token string, or None if unavailable
        """
        # Check if token needs refresh
        if self._needs_refresh(account):
            if not self._refresh_token(account):
                return None
        
        return decrypt_value(account.access_token_encrypted)
    
    def _needs_refresh(self, account: SocialAccount) -> bool:
        """Check if token needs to be refreshed."""
        if not account.token_expires_at:
            return False
        
        return datetime.utcnow() + self.TOKEN_REFRESH_BUFFER >= account.token_expires_at
    
    def _refresh_token(self, account: SocialAccount) -> bool:
        """
        Refresh an account's access token.
        
        Args:
            account: SocialAccount to refresh
            
        Returns:
            True if refresh succeeded
        """
        import asyncio
        import concurrent.futures
        
        if not account.refresh_token_encrypted:
            logger.warning(f"No refresh token for account {account.id}")
            account.status = "expired"
            self.db.commit()
            return False
        
        try:
            # Get platform-specific refresher
            from app.integrations.social import get_platform_client
            
            client = get_platform_client(account.platform)
            refresh_token = decrypt_value(account.refresh_token_encrypted)
            
            # The refresh_access_token method is async
            # Run it in a separate thread with its own event loop to avoid conflicts
            async def do_refresh():
                return await client.refresh_access_token(refresh_token=refresh_token)
            
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(do_refresh())
                finally:
                    loop.close()
            
            # Use a thread pool to run the async code
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                new_tokens = future.result(timeout=60)  # 60 second timeout
            
            if not new_tokens:
                logger.warning(f"Token refresh returned no tokens for account {account.id}")
                account.status = "expired"
                self.db.commit()
                return False
            
            # Update tokens
            account.access_token_encrypted = encrypt_value(new_tokens["access_token"])
            
            if new_tokens.get("refresh_token"):
                account.refresh_token_encrypted = encrypt_value(new_tokens["refresh_token"])
            
            if new_tokens.get("expires_at"):
                account.token_expires_at = new_tokens["expires_at"]
            elif new_tokens.get("expires_in"):
                account.token_expires_at = datetime.utcnow() + timedelta(
                    seconds=new_tokens["expires_in"]
                )
            
            account.status = "connected"
            self.db.commit()
            
            logger.info(f"Refreshed token for account {account.id}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to refresh token for account {account.id}")
            account.status = "error"
            self.db.commit()
            return False
    
    def mark_account_error(
        self,
        account: SocialAccount,
        error_message: str,
    ) -> None:
        """
        Mark an account as having an error.
        
        Args:
            account: SocialAccount instance
            error_message: Error description
        """
        account.status = "error"
        account.extra_metadata = account.extra_metadata or {}
        account.extra_metadata["last_error"] = error_message
        account.extra_metadata["error_at"] = datetime.utcnow().isoformat()
        
        self.db.commit()
        
        logger.warning(f"Marked account {account.id} as error: {error_message}")


def get_social_oauth_service(db: Session) -> SocialOAuthService:
    """Factory function to create a SocialOAuthService instance."""
    return SocialOAuthService(db)

