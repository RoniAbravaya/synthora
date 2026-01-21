"""
Stripe Webhook Handlers

Processes Stripe webhook events for subscription lifecycle management.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
import stripe

from app.core.config import settings
from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeWebhookHandler:
    """
    Handler for Stripe webhook events.
    
    Processes events related to:
    - Checkout session completion
    - Subscription creation, updates, and cancellation
    - Invoice payment success/failure
    - Customer updates
    """
    
    def __init__(self, db: Session):
        """
        Initialize the webhook handler.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify webhook signature and construct event.
        
        Args:
            payload: Raw request body
            signature: Stripe signature header
            
        Returns:
            Verified Stripe event
            
        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise ValueError("Invalid signature")
    
    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route event to appropriate handler.
        
        Args:
            event: Stripe event object
            
        Returns:
            Handler result
        """
        event_type = event["type"]
        data = event["data"]["object"]
        
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_failed,
            "customer.updated": self._handle_customer_updated,
        }
        
        handler = handlers.get(event_type)
        
        if handler:
            logger.info(f"Processing webhook event: {event_type}")
            return handler(data)
        else:
            logger.debug(f"Unhandled webhook event: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _handle_checkout_completed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle checkout.session.completed event.
        
        This is triggered when a customer completes checkout.
        """
        # Extract user ID from metadata
        user_id_str = data.get("metadata", {}).get("user_id")
        if not user_id_str:
            logger.error("Checkout completed without user_id in metadata")
            return {"status": "error", "reason": "missing user_id"}
        
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.error(f"Invalid user_id in metadata: {user_id_str}")
            return {"status": "error", "reason": "invalid user_id"}
        
        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found: {user_id}")
            return {"status": "error", "reason": "user not found"}
        
        # Get or create subscription record
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        plan_str = data.get("metadata", {}).get("plan", "monthly")
        
        try:
            plan = SubscriptionPlan(plan_str)
        except ValueError:
            plan = SubscriptionPlan.MONTHLY
        
        if subscription:
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.plan = plan
        else:
            subscription = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=SubscriptionStatus.ACTIVE,
                plan=plan,
            )
            self.db.add(subscription)
        
        # Upgrade user to premium
        user.role = UserRole.PREMIUM
        
        self.db.commit()
        
        logger.info(f"Checkout completed for user {user_id}, subscription {subscription_id}")
        
        return {
            "status": "success",
            "user_id": str(user_id),
            "subscription_id": subscription_id,
        }
    
    def _handle_subscription_created(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer.subscription.created event.
        
        This provides more details about the subscription.
        """
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")
        
        # Find subscription by Stripe ID
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            # Try to find by customer ID
            subscription = self.db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).first()
        
        if subscription:
            # Update period dates
            subscription.current_period_start = datetime.fromtimestamp(
                data.get("current_period_start", 0)
            )
            subscription.current_period_end = datetime.fromtimestamp(
                data.get("current_period_end", 0)
            )
            subscription.stripe_subscription_id = subscription_id
            
            # Map Stripe status
            subscription.status = self._map_stripe_status(status)
            
            self.db.commit()
            
            logger.info(f"Subscription created: {subscription_id}")
        
        return {"status": "success", "subscription_id": subscription_id}
    
    def _handle_subscription_updated(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer.subscription.updated event.
        
        This is triggered when subscription details change.
        """
        subscription_id = data.get("id")
        status = data.get("status")
        cancel_at_period_end = data.get("cancel_at_period_end", False)
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "not_found", "subscription_id": subscription_id}
        
        # Update subscription
        subscription.status = self._map_stripe_status(status)
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.current_period_start = datetime.fromtimestamp(
            data.get("current_period_start", 0)
        )
        subscription.current_period_end = datetime.fromtimestamp(
            data.get("current_period_end", 0)
        )
        
        if data.get("canceled_at"):
            subscription.canceled_at = datetime.fromtimestamp(data["canceled_at"])
        
        # Update user role based on status
        user = self.db.query(User).filter(User.id == subscription.user_id).first()
        if user:
            if subscription.status == SubscriptionStatus.ACTIVE:
                user.role = UserRole.PREMIUM
            elif subscription.status in [SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED]:
                if user.role == UserRole.PREMIUM:
                    user.role = UserRole.FREE
        
        self.db.commit()
        
        logger.info(f"Subscription updated: {subscription_id}, status: {status}")
        
        return {"status": "success", "subscription_id": subscription_id}
    
    def _handle_subscription_deleted(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer.subscription.deleted event.
        
        This is triggered when a subscription is cancelled.
        """
        subscription_id = data.get("id")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for deletion: {subscription_id}")
            return {"status": "not_found", "subscription_id": subscription_id}
        
        # Update subscription
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.utcnow()
        
        # Downgrade user
        user = self.db.query(User).filter(User.id == subscription.user_id).first()
        if user and user.role == UserRole.PREMIUM:
            user.role = UserRole.FREE
        
        self.db.commit()
        
        logger.info(f"Subscription deleted: {subscription_id}")
        
        return {"status": "success", "subscription_id": subscription_id}
    
    def _handle_invoice_paid(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle invoice.payment_succeeded event.
        
        This confirms successful payment.
        """
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")
        amount_paid = data.get("amount_paid", 0) / 100  # Convert from cents
        
        if subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if subscription:
                # Ensure subscription is active
                subscription.status = SubscriptionStatus.ACTIVE
                
                # Update period dates from lines
                lines = data.get("lines", {}).get("data", [])
                for line in lines:
                    if line.get("type") == "subscription":
                        period = line.get("period", {})
                        if period.get("start"):
                            subscription.current_period_start = datetime.fromtimestamp(period["start"])
                        if period.get("end"):
                            subscription.current_period_end = datetime.fromtimestamp(period["end"])
                
                # Ensure user is premium
                user = self.db.query(User).filter(User.id == subscription.user_id).first()
                if user and user.role != UserRole.PREMIUM:
                    user.role = UserRole.PREMIUM
                
                self.db.commit()
        
        logger.info(f"Invoice paid: ${amount_paid} for subscription {subscription_id}")
        
        return {
            "status": "success",
            "subscription_id": subscription_id,
            "amount": amount_paid,
        }
    
    def _handle_invoice_failed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle invoice.payment_failed event.
        
        This indicates a payment failure.
        """
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")
        attempt_count = data.get("attempt_count", 0)
        
        if subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if subscription:
                # Update status to past_due
                subscription.status = SubscriptionStatus.PAST_DUE
                self.db.commit()
                
                # TODO: Send notification to user about failed payment
                logger.warning(
                    f"Payment failed for subscription {subscription_id}, "
                    f"attempt {attempt_count}"
                )
        
        return {
            "status": "recorded",
            "subscription_id": subscription_id,
            "attempt_count": attempt_count,
        }
    
    def _handle_customer_updated(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer.updated event.
        
        This is triggered when customer details change.
        """
        customer_id = data.get("id")
        email = data.get("email")
        
        # Find subscription with this customer
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            # Could update user email if changed
            # For now, just log it
            logger.info(f"Customer updated: {customer_id}")
        
        return {"status": "success", "customer_id": customer_id}
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _map_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """Map Stripe subscription status to our enum."""
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "unpaid": SubscriptionStatus.PAST_DUE,
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "incomplete_expired": SubscriptionStatus.EXPIRED,
            "trialing": SubscriptionStatus.TRIALING,
            "paused": SubscriptionStatus.PAUSED,
        }
        return status_map.get(stripe_status, SubscriptionStatus.INCOMPLETE)


def get_webhook_handler(db: Session) -> StripeWebhookHandler:
    """Factory function to create a StripeWebhookHandler instance."""
    return StripeWebhookHandler(db)

