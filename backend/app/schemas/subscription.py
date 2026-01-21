"""
Subscription Pydantic Schemas

Request and response schemas for subscription-related endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.models.subscription import SubscriptionPlan, SubscriptionStatus


# =============================================================================
# Response Schemas
# =============================================================================

class SubscriptionResponse(BaseSchema):
    """Full subscription response."""
    
    id: str
    status: str
    plan: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SubscriptionStatusResponse(BaseSchema):
    """Current subscription status for user."""
    
    has_subscription: bool = False
    plan: Optional[str] = Field(default=None, description="Current plan (free, monthly, annual)")
    status: Optional[str] = Field(default=None, description="Subscription status")
    current_period_start: Optional[datetime] = Field(default=None, description="Period start date")
    current_period_end: Optional[datetime] = Field(default=None, description="Period end date")
    cancel_at_period_end: bool = Field(default=False, description="Will cancel at period end")
    days_until_renewal: Optional[int] = Field(default=None, description="Days until next renewal")


class PlanFeatures(BaseSchema):
    """Features for a subscription plan."""
    
    videos_per_day: Optional[int] = Field(description="Videos per day (null=unlimited)")
    scheduling: bool = Field(description="Can schedule posts")
    ai_suggestions: bool = Field(description="Can access AI suggestions")
    video_retention_days: Optional[int] = Field(description="Video retention (null=unlimited)")
    all_integrations: bool = Field(description="Access to all integrations")


class PlanInfo(BaseSchema):
    """Information about a subscription plan."""
    
    id: str = Field(description="Plan ID (free, monthly, annual)")
    name: str = Field(description="Plan display name")
    price: float = Field(description="Price in USD")
    interval: Optional[str] = Field(default=None, description="Billing interval")
    stripe_price_id: Optional[str] = Field(default=None, description="Stripe price ID")
    savings: Optional[str] = Field(default=None, description="Savings description")
    features: List[str] = Field(description="List of feature descriptions")


class PlansResponse(BaseSchema):
    """Available subscription plans."""
    
    plans: List[PlanInfo]


class InvoiceItem(BaseSchema):
    """Invoice item details."""
    
    id: str
    number: Optional[str] = None
    status: str
    amount_due: float
    amount_paid: float
    currency: str
    created: datetime
    invoice_pdf: Optional[str] = None
    hosted_invoice_url: Optional[str] = None


class InvoicesResponse(BaseSchema):
    """List of invoices."""
    
    invoices: List[InvoiceItem]


class UpcomingInvoiceItem(BaseSchema):
    """Upcoming invoice line item."""
    
    description: str
    amount: float


class UpcomingInvoiceResponse(BaseSchema):
    """Upcoming invoice details."""
    
    amount_due: float
    currency: str
    next_payment_date: Optional[datetime] = None
    lines: List[UpcomingInvoiceItem]


# =============================================================================
# Request Schemas
# =============================================================================

class CheckoutRequest(BaseSchema):
    """Request to create checkout session."""
    
    plan: str = Field(description="Plan to subscribe to (monthly, annual)")
    success_url: Optional[str] = Field(default=None, description="URL to redirect on success")
    cancel_url: Optional[str] = Field(default=None, description="URL to redirect on cancel")


class CheckoutResponse(BaseSchema):
    """Checkout session response."""
    
    checkout_url: str = Field(description="Stripe Checkout URL")
    session_id: str = Field(description="Stripe session ID")


class PortalRequest(BaseSchema):
    """Request for customer portal session."""
    
    return_url: Optional[str] = Field(default=None, description="URL to return to after portal")


class PortalResponse(BaseSchema):
    """Customer portal session response."""
    
    portal_url: str = Field(description="Stripe Customer Portal URL")


class CancelRequest(BaseSchema):
    """Request to cancel subscription."""
    
    immediately: bool = Field(default=False, description="Cancel immediately or at period end")


class ChangePlanRequest(BaseSchema):
    """Request to change subscription plan."""
    
    plan: str = Field(description="New plan (monthly, annual)")


# =============================================================================
# Admin Schemas
# =============================================================================

class GrantPremiumRequest(BaseSchema):
    """Request to grant premium access."""
    
    user_id: UUID = Field(description="User to grant premium to")
    days: int = Field(default=30, ge=1, le=365, description="Number of days")
    reason: Optional[str] = Field(default="Admin grant", description="Reason for grant")


class RevokePremiumRequest(BaseSchema):
    """Request to revoke premium access."""
    
    user_id: UUID = Field(description="User to revoke premium from")


class SubscriptionStatsResponse(BaseSchema):
    """Subscription statistics for admin dashboard."""
    
    total_subscriptions: int
    by_status: Dict[str, int]
    by_plan: Dict[str, int]
    mrr: float = Field(description="Monthly Recurring Revenue")
    arr: float = Field(description="Annual Recurring Revenue")


# =============================================================================
# Webhook Schemas
# =============================================================================

class WebhookResponse(BaseSchema):
    """Webhook acknowledgement response."""
    
    received: bool = True
    status: Optional[str] = None

