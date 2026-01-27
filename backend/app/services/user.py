"""
User Service

Business logic for user management operations.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.integration import Integration
from app.models.video import Video
from app.models.post import Post
from app.services.firebase import UserInfo

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related operations.
    
    This class encapsulates all business logic for user management,
    including CRUD operations, role management, and statistics.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the user service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by their UUID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by their email address.
        
        Args:
            email: User's email address
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """
        Get a user by their Firebase UID.
        
        Args:
            firebase_uid: Firebase authentication UID
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.firebase_uid == firebase_uid).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[List[User], int]:
        """
        Get all users with optional filtering and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Filter by role
            is_active: Filter by active status
            search: Search by email or name
            
        Returns:
            Tuple of (list of users, total count)
        """
        query = self.db.query(User)
        
        # Apply filters
        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_term)) | (User.display_name.ilike(search_term))
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return users, total
    
    # =========================================================================
    # Create/Update Methods
    # =========================================================================
    
    def create_user(
        self,
        firebase_user: UserInfo,
        role: str = "free",
    ) -> User:
        """
        Create a new user from Firebase authentication info.
        
        Args:
            firebase_user: Verified Firebase user information
            role: Initial role for the user (default: FREE)
            
        Returns:
            Newly created User instance
        """
        user = User(
            email=firebase_user.email,
            display_name=firebase_user.name,
            photo_url=firebase_user.picture,
            firebase_uid=firebase_user.uid,
            role=role,
            is_active=True,
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Created new user: {user.email} with role {role}")
        return user
    
    def create_or_update_from_firebase(self, firebase_user: UserInfo) -> tuple[User, bool]:
        """
        Create a new user or update existing user from Firebase login.
        
        This is the main method called during login to ensure the user
        exists in our database and their info is up to date.
        
        Args:
            firebase_user: Verified Firebase user information
            
        Returns:
            Tuple of (User instance, is_new_user boolean)
        """
        user = self.get_by_firebase_uid(firebase_user.uid)
        
        if user:
            # Update existing user profile info if changed
            if firebase_user.name and user.display_name != firebase_user.name:
                user.display_name = firebase_user.name
            if firebase_user.picture and user.photo_url != firebase_user.picture:
                user.photo_url = firebase_user.picture
            
            # Update last login timestamp
            user.last_login = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User logged in: {user.email}")
            return user, False
        
        # Create new user
        # Check if this should be the first admin
        role = "free"
        if self._should_be_first_admin():
            role = "admin"
            logger.info("First user - assigning admin role")
        
        user = self.create_user(firebase_user, role=role)
        # Set first login time
        user.last_login = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user, True
    
    def update_user(
        self,
        user: User,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> User:
        """
        Update user profile information.
        
        Args:
            user: User instance to update
            display_name: New display name (optional)
            photo_url: New avatar URL (optional)
            
        Returns:
            Updated User instance
        """
        if display_name is not None:
            user.display_name = display_name
        if photo_url is not None:
            user.photo_url = photo_url
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Updated user profile: {user.email}")
        return user
    
    def update_role(self, user: User, new_role: str) -> User:
        """
        Update a user's role.
        
        Args:
            user: User instance to update
            new_role: New role to assign
            
        Returns:
            Updated User instance
        """
        old_role = user.role
        user.role = new_role
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Updated user role: {user.email} from {old_role} to {new_role}")
        return user
    
    def set_active_status(self, user: User, is_active: bool) -> User:
        """
        Enable or disable a user account.
        
        Args:
            user: User instance to update
            is_active: New active status
            
        Returns:
            Updated User instance
        """
        user.is_active = is_active
        
        self.db.commit()
        self.db.refresh(user)
        
        status = "enabled" if is_active else "disabled"
        logger.info(f"User account {status}: {user.email}")
        return user
    
    def make_admin_by_email(self, email: str) -> Optional[User]:
        """
        Make a user admin by their email address.
        
        Args:
            email: User's email address
            
        Returns:
            Updated User instance or None if not found
        """
        user = self.get_by_email(email)
        if user:
            return self.update_role(user, "admin")
        return None
    
    # =========================================================================
    # Statistics Methods
    # =========================================================================
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        Get platform-wide user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        # Total users
        total = self.db.query(User).count()
        
        # Users by role
        by_role = {}
        for role in ["admin", "premium", "free"]:
            count = self.db.query(User).filter(User.role == role).count()
            by_role[role] = count
        
        # Active users
        active = self.db.query(User).filter(User.is_active == True).count()
        
        # New users this month
        from datetime import datetime, timedelta
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_this_month = self.db.query(User).filter(
            User.created_at >= month_ago
        ).count()
        
        return {
            "total": total,
            "by_role": by_role,
            "active": active,
            "new_this_month": new_this_month,
        }
    
    def get_user_profile_data(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive profile data for a user.
        
        Includes subscription status, feature access, and usage stats.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with profile data
        """
        # Get subscription info
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        subscription_plan = None
        subscription_status = None
        if subscription:
            subscription_plan = subscription.plan
            subscription_status = subscription.status
        
        # Count user's content
        videos_count = self.db.query(Video).filter(Video.user_id == user.id).count()
        posts_count = self.db.query(Post).filter(Post.user_id == user.id).count()
        integrations_count = self.db.query(Integration).filter(
            and_(Integration.user_id == user.id, Integration.is_active == True)
        ).count()
        
        return {
            "subscription_plan": subscription_plan,
            "subscription_status": subscription_status,
            "can_schedule": user.can_schedule,
            "can_access_ai_suggestions": user.can_access_ai_suggestions,
            "daily_video_limit": user.daily_video_limit,
            "videos_count": videos_count,
            "posts_count": posts_count,
            "integrations_configured": integrations_count,
        }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _should_be_first_admin(self) -> bool:
        """
        Check if the next user should be the first admin.
        
        Returns True if no admin exists yet (first user setup).
        """
        admin_exists = self.db.query(User).filter(
            User.role == "admin"
        ).first() is not None
        
        return not admin_exists
    
    def admin_exists(self) -> bool:
        """
        Check if any admin user exists.
        
        Used to determine if initial setup is complete.
        """
        return self.db.query(User).filter(
            User.role == "admin"
        ).first() is not None
    
    def get_admin_count(self) -> int:
        """Get the number of admin users."""
        return self.db.query(User).filter(User.role == "admin").count()


def get_user_service(db: Session) -> UserService:
    """
    Factory function to create a UserService instance.
    
    Use this as a FastAPI dependency:
    ```python
    @router.get("/users")
    def list_users(
        user_service: UserService = Depends(get_user_service)
    ):
        ...
    ```
    """
    return UserService(db)
