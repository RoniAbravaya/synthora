"""
Subscription API Endpoints

Endpoints for subscription management and Stripe integration.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.auth import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.models.subscription import SubscriptionPlan
from app.services.stripe_service import StripeService
from app.services.stripe_webhooks import StripeWebhookHandler
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionStatusResponse,
    PlanInfo,
    PlansResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalRequest,
    PortalResponse,
    CancelRequest,
    ChangePlanRequest,
    InvoicesResponse,
    InvoiceItem,
    UpcomingInvoiceResponse,
    UpcomingInvoiceItem,
    GrantPremiumRequest,
    RevokePremiumRequest,
    SubscriptionStatsResponse,
    WebhookResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# =============================================================================
# Plan Information
# =============================================================================

@router.get("/plans", response_model=PlansResponse)
async def get_available_plans():
    """
    Get available subscription plans.
    
    Returns pricing and feature information for all plans.
    """
    settings = get_settings()
    plans = [
        PlanInfo(
            id="free",
            name="Free",
            price=0.0,
            interval=None,
            stripe_price_id=None,
            savings=None,
            features=[
                "1 video per day",
                "Basic integrations",
                "30-day video retention",
                "Manual posting only",
            ],
        ),
        PlanInfo(
            id="monthly",
            name="Premium Monthly",
            price=5.0,
            interval="month",
            stripe_price_id=settings.STRIPE_MONTHLY_PRICE_ID,
            savings=None,
            features=[
                "Unlimited videos",
                "All integrations",
                "Unlimited video retention",
                "Post scheduling",
                "AI suggestions",
                "Advanced analytics",
            ],
        ),
        PlanInfo(
            id="annual",
            name="Premium Annual",
            price=50.0,
            interval="year",
            stripe_price_id=settings.STRIPE_ANNUAL_PRICE_ID,
            savings="Save $10/year (2 months free!)",
            features=[
                "Unlimited videos",
                "All integrations",
                "Unlimited video retention",
                "Post scheduling",
                "AI suggestions",
                "Advanced analytics",
                "Priority support",
            ],
        ),
    ]
    
    return PlansResponse(plans=plans)


# =============================================================================
# Subscription Status
# =============================================================================

@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's subscription status.
    """
    service = StripeService(db)
    subscription = service.get_subscription_status(current_user.id)
    
    if not subscription:
        return SubscriptionStatusResponse(
            has_subscription=False,
            plan="free",
            status="none",
        )
    
    # Calculate days until renewal
    days_until_renewal = None
    if subscription.get("current_period_end"):
        delta = subscription["current_period_end"] - datetime.utcnow()
        days_until_renewal = max(0, delta.days)
    
    return SubscriptionStatusResponse(
        has_subscription=True,
        plan=subscription.get("plan"),
        status=subscription.get("status"),
        current_period_start=subscription.get("current_period_start"),
        current_period_end=subscription.get("current_period_end"),
        cancel_at_period_end=subscription.get("cancel_at_period_end", False),
        days_until_renewal=days_until_renewal,
    )


@router.get("/details", response_model=SubscriptionResponse)
async def get_subscription_details(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed subscription information.
    """
    service = StripeService(db)
    subscription = service.get_subscription_status(current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found",
        )
    
    return SubscriptionResponse(**subscription)


# =============================================================================
# Checkout & Portal
# =============================================================================

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscription.
    """
    settings = get_settings()
    
    # Validate plan
    try:
        plan = SubscriptionPlan(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}. Must be 'monthly' or 'annual'.",
        )
    
    # Check if user already has active subscription
    service = StripeService(db)
    existing = service.get_subscription_status(current_user.id)
    
    if existing and existing.get("status") == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription. Use the portal to manage it.",
        )
    
    # Set default URLs
    base_url = settings.FRONTEND_URL or "http://localhost:5173"
    success_url = request.success_url or f"{base_url}/settings/subscription?success=true"
    cancel_url = request.cancel_url or f"{base_url}/settings/subscription?canceled=true"
    
    try:
        result = service.create_checkout_session(
            user=current_user,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        
        return CheckoutResponse(
            checkout_url=result["url"],
            session_id=result["session_id"],
        )
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Customer Portal session.
    
    Allows users to manage their subscription, update payment methods, etc.
    """
    settings = get_settings()
    service = StripeService(db)
    
    # Set default return URL
    base_url = settings.FRONTEND_URL or "http://localhost:5173"
    return_url = request.return_url or f"{base_url}/settings/subscription"
    
    try:
        result = service.create_portal_session(
            user=current_user,
            return_url=return_url,
        )
        
        return PortalResponse(portal_url=result["url"])
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )


# =============================================================================
# Subscription Management
# =============================================================================

@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    request: CancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Cancel subscription.
    
    By default, cancels at the end of the current billing period.
    Set immediately=true to cancel immediately (no refund).
    """
    service = StripeService(db)
    
    try:
        result = service.cancel_subscription(
            user_id=current_user.id,
            immediately=request.immediately,
        )
        
        return SubscriptionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.post("/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reactivate a subscription that was set to cancel at period end.
    """
    service = StripeService(db)
    
    try:
        result = service.reactivate_subscription(current_user.id)
        return SubscriptionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to reactivate subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription",
        )


@router.post("/change-plan", response_model=SubscriptionResponse)
async def change_subscription_plan(
    request: ChangePlanRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change subscription plan (upgrade/downgrade).
    
    Proration will be applied automatically.
    """
    # Validate plan
    try:
        plan = SubscriptionPlan(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}",
        )
    
    service = StripeService(db)
    
    try:
        result = service.change_plan(current_user.id, plan)
        return SubscriptionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to change plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change plan",
        )


# =============================================================================
# Invoices
# =============================================================================

@router.get("/invoices", response_model=InvoicesResponse)
async def get_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get invoice history.
    """
    service = StripeService(db)
    invoices = service.get_invoices(current_user.id, limit)
    
    return InvoicesResponse(
        invoices=[InvoiceItem(**inv) for inv in invoices]
    )


@router.get("/invoices/upcoming", response_model=UpcomingInvoiceResponse)
async def get_upcoming_invoice(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get upcoming invoice details.
    """
    service = StripeService(db)
    invoice = service.get_upcoming_invoice(current_user.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No upcoming invoice",
        )
    
    return UpcomingInvoiceResponse(
        amount_due=invoice["amount_due"],
        currency=invoice["currency"],
        next_payment_date=invoice.get("next_payment_date"),
        lines=[UpcomingInvoiceItem(**line) for line in invoice.get("lines", [])],
    )


# =============================================================================
# Webhooks
# =============================================================================

@router.post("/webhook", response_model=WebhookResponse)
async def handle_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives events from Stripe for subscription lifecycle management.
    """
    # Get raw body and signature
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )
    
    handler = StripeWebhookHandler(db)
    
    try:
        # Verify and construct event
        event = handler.verify_webhook(payload, signature)
        
        # Handle the event
        result = handler.handle_event(event)
        
        return WebhookResponse(received=True, status=result.get("status"))
        
    except ValueError as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        # Return 200 to acknowledge receipt even on error
        # (Stripe will retry otherwise)
        return WebhookResponse(received=True, status="error")


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/admin/grant-premium", response_model=SubscriptionResponse)
async def admin_grant_premium(
    request: GrantPremiumRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Grant premium access to a user (admin only).
    """
    service = StripeService(db)
    
    try:
        result = service.grant_premium(
            user_id=request.user_id,
            days=request.days,
            reason=request.reason or "Admin grant",
        )
        
        return SubscriptionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/admin/revoke-premium")
async def admin_revoke_premium(
    request: RevokePremiumRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Revoke premium access from a user (admin only).
    """
    service = StripeService(db)
    
    try:
        service.revoke_premium(request.user_id)
        return {"message": "Premium access revoked"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/admin/stats", response_model=SubscriptionStatsResponse)
async def get_subscription_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get subscription statistics (admin only).
    """
    service = StripeService(db)
    stats = service.get_subscription_stats()
    
    return SubscriptionStatsResponse(**stats)
