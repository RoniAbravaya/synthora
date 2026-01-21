"""
Stripe Service

Business logic for Stripe payment processing and subscription management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
import stripe

from app.core.config import settings
from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """
    Service class for Stripe payment operations.
    
    Handles:
    - Creating checkout sessions
    - Managing customer portal sessions
    - Processing webhooks
    - Subscription lifecycle management
    """
    
    # Price IDs from Stripe Dashboard
    # These should be configured in environment variables
    PRICE_IDS = {
        SubscriptionPlan.MONTHLY: settings.STRIPE_MONTHLY_PRICE_ID,
        SubscriptionPlan.ANNUAL: settings.STRIPE_ANNUAL_PRICE_ID,
    }
    
    def __init__(self, db: Session):
        """
        Initialize the Stripe service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # =========================================================================
    # Customer Management
    # =========================================================================
    
    def get_or_create_customer(self, user: User) -> str:
        """
        Get or create a Stripe customer for a user.
        
        Args:
            user: User model instance
            
        Returns:
            Stripe customer ID
        """
        # Check if user already has a customer ID
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id
        
        # Create new Stripe customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.display_name,
                metadata={
                    "user_id": str(user.id),
                    "firebase_uid": user.firebase_uid,
                },
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise
    
    def update_customer(self, customer_id: str, **kwargs) -> None:
        """Update Stripe customer details."""
        try:
            stripe.Customer.modify(customer_id, **kwargs)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer: {e}")
            raise
    
    # =========================================================================
    # Checkout Sessions
    # =========================================================================
    
    def create_checkout_session(
        self,
        user: User,
        plan: SubscriptionPlan,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            user: User model instance
            plan: Subscription plan (monthly/annual)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            
        Returns:
            Dictionary with checkout session details
        """
        customer_id = self.get_or_create_customer(user)
        price_id = self.PRICE_IDS.get(plan)
        
        if not price_id:
            raise ValueError(f"No price ID configured for plan: {plan}")
        
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "plan": plan.value,
                },
                subscription_data={
                    "metadata": {
                        "user_id": str(user.id),
                        "plan": plan.value,
                    },
                },
                allow_promotion_codes=True,
            )
            
            logger.info(f"Created checkout session {session.id} for user {user.id}")
            
            return {
                "session_id": session.id,
                "url": session.url,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise
    
    def create_portal_session(
        self,
        user: User,
        return_url: str,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Customer Portal session.
        
        Allows users to manage their subscription, update payment methods, etc.
        
        Args:
            user: User model instance
            return_url: URL to redirect after portal session
            
        Returns:
            Dictionary with portal session details
        """
        # Get customer ID
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if not subscription or not subscription.stripe_customer_id:
            raise ValueError("User does not have an active subscription")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url,
            )
            
            return {
                "url": session.url,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise
    
    # =========================================================================
    # Subscription Management
    # =========================================================================
    
    def get_subscription_status(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get subscription status for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Subscription details or None
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            return None
        
        return {
            "id": str(subscription.id),
            "status": subscription.status.value,
            "plan": subscription.plan.value if subscription.plan else None,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": subscription.canceled_at,
            "created_at": subscription.created_at,
        }
    
    def cancel_subscription(
        self,
        user_id: UUID,
        immediately: bool = False,
    ) -> Dict[str, Any]:
        """
        Cancel a user's subscription.
        
        Args:
            user_id: User UUID
            immediately: If True, cancel immediately. Otherwise, cancel at period end.
            
        Returns:
            Updated subscription details
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found")
        
        try:
            if immediately:
                # Cancel immediately
                stripe_sub = stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
            else:
                # Cancel at period end
                stripe_sub = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
            
            # Update local record
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
            if immediately:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                
                # Downgrade user role
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and user.role == UserRole.PREMIUM:
                    user.role = UserRole.FREE
            
            self.db.commit()
            
            logger.info(f"Cancelled subscription for user {user_id}")
            
            return self.get_subscription_status(user_id)
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise
    
    def reactivate_subscription(self, user_id: UUID) -> Dict[str, Any]:
        """
        Reactivate a subscription that was set to cancel at period end.
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated subscription details
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.cancel_at_period_end == True,
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No subscription to reactivate")
        
        try:
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )
            
            subscription.cancel_at_period_end = False
            self.db.commit()
            
            logger.info(f"Reactivated subscription for user {user_id}")
            
            return self.get_subscription_status(user_id)
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            raise
    
    def change_plan(
        self,
        user_id: UUID,
        new_plan: SubscriptionPlan,
    ) -> Dict[str, Any]:
        """
        Change subscription plan (upgrade/downgrade).
        
        Args:
            user_id: User UUID
            new_plan: New subscription plan
            
        Returns:
            Updated subscription details
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found")
        
        new_price_id = self.PRICE_IDS.get(new_plan)
        if not new_price_id:
            raise ValueError(f"No price ID configured for plan: {new_plan}")
        
        try:
            # Get current subscription
            stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )
            
            # Update subscription with new price
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[
                    {
                        "id": stripe_sub["items"]["data"][0]["id"],
                        "price": new_price_id,
                    }
                ],
                proration_behavior="create_prorations",
            )
            
            # Update local record
            subscription.plan = new_plan
            self.db.commit()
            
            logger.info(f"Changed plan to {new_plan.value} for user {user_id}")
            
            return self.get_subscription_status(user_id)
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to change plan: {e}")
            raise
    
    # =========================================================================
    # Invoice & Payment History
    # =========================================================================
    
    def get_invoices(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get invoice history for a user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of invoices
            
        Returns:
            List of invoice details
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription or not subscription.stripe_customer_id:
            return []
        
        try:
            invoices = stripe.Invoice.list(
                customer=subscription.stripe_customer_id,
                limit=limit,
            )
            
            return [
                {
                    "id": inv.id,
                    "number": inv.number,
                    "status": inv.status,
                    "amount_due": inv.amount_due / 100,  # Convert from cents
                    "amount_paid": inv.amount_paid / 100,
                    "currency": inv.currency.upper(),
                    "created": datetime.fromtimestamp(inv.created),
                    "invoice_pdf": inv.invoice_pdf,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                }
                for inv in invoices.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get invoices: {e}")
            return []
    
    def get_upcoming_invoice(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get upcoming invoice for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Upcoming invoice details or None
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        ).first()
        
        if not subscription or not subscription.stripe_customer_id:
            return None
        
        try:
            invoice = stripe.Invoice.upcoming(
                customer=subscription.stripe_customer_id,
            )
            
            return {
                "amount_due": invoice.amount_due / 100,
                "currency": invoice.currency.upper(),
                "next_payment_date": datetime.fromtimestamp(invoice.next_payment_attempt) if invoice.next_payment_attempt else None,
                "lines": [
                    {
                        "description": line.description,
                        "amount": line.amount / 100,
                    }
                    for line in invoice.lines.data
                ],
            }
            
        except stripe.error.InvalidRequestError:
            # No upcoming invoice (e.g., subscription cancelled)
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get upcoming invoice: {e}")
            return None
    
    # =========================================================================
    # Admin Functions
    # =========================================================================
    
    def grant_premium(
        self,
        user_id: UUID,
        days: int = 30,
        reason: str = "Admin grant",
    ) -> Dict[str, Any]:
        """
        Grant premium access to a user without payment.
        
        Args:
            user_id: User UUID
            days: Number of days to grant
            reason: Reason for grant
            
        Returns:
            Subscription details
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Check for existing subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)
        
        if subscription:
            # Extend existing subscription
            if subscription.current_period_end and subscription.current_period_end > now:
                end_date = subscription.current_period_end + timedelta(days=days)
            
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = now
            subscription.current_period_end = end_date
            subscription.plan = SubscriptionPlan.MONTHLY  # Default to monthly for grants
            subscription.cancel_at_period_end = False
        else:
            # Create new subscription record
            subscription = Subscription(
                user_id=user_id,
                status=SubscriptionStatus.ACTIVE,
                plan=SubscriptionPlan.MONTHLY,
                current_period_start=now,
                current_period_end=end_date,
            )
            self.db.add(subscription)
        
        # Upgrade user role
        user.role = UserRole.PREMIUM
        
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Granted {days} days premium to user {user_id}: {reason}")
        
        return self.get_subscription_status(user_id)
    
    def revoke_premium(self, user_id: UUID) -> None:
        """
        Revoke premium access from a user.
        
        Args:
            user_id: User UUID
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if subscription:
            # Cancel Stripe subscription if exists
            if subscription.stripe_subscription_id:
                try:
                    stripe.Subscription.delete(subscription.stripe_subscription_id)
                except stripe.error.StripeError:
                    pass  # May already be cancelled
            
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
        
        # Downgrade user
        if user.role == UserRole.PREMIUM:
            user.role = UserRole.FREE
        
        self.db.commit()
        
        logger.info(f"Revoked premium from user {user_id}")
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """
        Get subscription statistics for admin dashboard.
        
        Returns:
            Subscription statistics
        """
        from sqlalchemy import func
        
        # Count by status
        status_counts = dict(
            self.db.query(
                Subscription.status,
                func.count(Subscription.id),
            ).group_by(Subscription.status).all()
        )
        
        # Count by plan
        plan_counts = dict(
            self.db.query(
                Subscription.plan,
                func.count(Subscription.id),
            ).filter(
                Subscription.status == SubscriptionStatus.ACTIVE
            ).group_by(Subscription.plan).all()
        )
        
        # Calculate MRR (Monthly Recurring Revenue)
        monthly_count = plan_counts.get(SubscriptionPlan.MONTHLY, 0)
        annual_count = plan_counts.get(SubscriptionPlan.ANNUAL, 0)
        
        monthly_price = 5.00  # $5/month
        annual_price = 50.00  # $50/year = ~$4.17/month
        
        mrr = (monthly_count * monthly_price) + (annual_count * (annual_price / 12))
        
        return {
            "total_subscriptions": sum(status_counts.values()),
            "by_status": {
                status.value if status else "none": count
                for status, count in status_counts.items()
            },
            "by_plan": {
                plan.value if plan else "none": count
                for plan, count in plan_counts.items()
            },
            "mrr": round(mrr, 2),
            "arr": round(mrr * 12, 2),
        }


def get_stripe_service(db: Session) -> StripeService:
    """Factory function to create a StripeService instance."""
    return StripeService(db)

