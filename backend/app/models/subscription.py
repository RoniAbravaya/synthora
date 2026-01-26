"""
Subscription Model

Represents a user's Stripe subscription for premium features.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan types."""
    FREE = "free"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, enum.Enum):
    """
    Subscription status values.
    
    - active: Subscription is active and paid
    - past_due: Payment failed, in grace period
    - canceled: User canceled, still active until period end
    - unpaid: Multiple failed payments
    - incomplete: Initial payment not completed
    - trialing: In trial period (not used currently)
    """
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"


class Subscription(Base, UUIDMixin, TimestampMixin):
    """
    Subscription model for tracking Stripe subscriptions.
    
    This model matches the database schema from migration 001_initial_schema.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user
        plan: Subscription plan (free/monthly/annual) - stored as string
        status: Current subscription status - stored as string
        stripe_subscription_id: Stripe subscription ID
        stripe_price_id: Stripe price ID
        current_period_start: Start of current billing period
        current_period_end: End of current billing period
        cancel_at_period_end: Whether subscription cancels at period end
        canceled_at: When the subscription was canceled
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    
    Relationships:
        user: The user who owns this subscription
    """
    
    __tablename__ = "subscriptions"
    
    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Foreign key to user"
    )
    
    # Plan Details - stored as strings in DB (not PostgreSQL ENUM)
    plan = Column(
        String(20),
        nullable=False,
        default="free",
        doc="Subscription plan type"
    )
    status = Column(
        String(20),
        default="active",
        nullable=False,
        index=True,
        doc="Current subscription status"
    )
    
    # Stripe IDs
    stripe_subscription_id = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="Stripe subscription ID"
    )
    stripe_price_id = Column(
        String(255),
        nullable=True,
        doc="Stripe price ID"
    )
    
    # Billing Period
    current_period_start = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Start of current billing period"
    )
    current_period_end = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="End of current billing period"
    )
    
    # Cancellation
    cancel_at_period_end = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether subscription cancels at period end"
    )
    canceled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the subscription was canceled"
    )
    
    # Relationship
    user = relationship("User", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status in ("active", "trialing")
    
    @property
    def is_valid(self) -> bool:
        """
        Check if subscription is valid (active or in grace period).
        Users with past_due status still have access during grace period.
        """
        return self.status in ("active", "trialing", "past_due")
    
    @property
    def days_until_renewal(self) -> Optional[int]:
        """Get number of days until next renewal."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def price(self) -> float:
        """Get the price for this plan."""
        if self.plan == "monthly":
            return 5.00
        elif self.plan == "annual":
            return 50.00
        return 0.00
