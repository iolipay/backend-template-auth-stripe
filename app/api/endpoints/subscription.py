from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from app.api.deps import get_current_user, get_stripe_service
from app.schemas.user import UserResponse
from app.schemas.subscription import CheckoutSessionCreate, CheckoutSessionResponse, UserSubscriptionResponse, BillingPortalResponse
from app.services.stripe import StripeService
from app.core.subscription import require_subscription, SubscriptionLevel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Subscription"])

@router.get("/free")
async def free_page():
    """Free plan page - accessible to all users"""
    return {"message": "free page"}

@router.get("/pro")
@require_subscription(SubscriptionLevel.PRO)
async def pro_page(current_user: UserResponse = Depends(get_current_user)):
    """Pro plan page - requires Pro or Premium subscription"""
    return {"message": "pro page"}

@router.get("/premium")
@require_subscription(SubscriptionLevel.PREMIUM)
async def premium_page(current_user: UserResponse = Depends(get_current_user)):
    """Premium plan page - requires Premium subscription"""
    return {"message": "premium page"}

@router.post("/create-checkout-session", 
    response_model=CheckoutSessionResponse,
    description="Create a Stripe checkout session for subscription",
    responses={
        200: {"description": "Checkout session created successfully or subscription change rejected"},
        400: {"description": "Invalid price ID or Stripe error"},
        401: {"description": "Not authenticated"}
    })
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
) -> CheckoutSessionResponse:
    """
    Create a Stripe checkout session for subscription.
    
    Parameters:
    - price_id: Your Stripe Price ID (Pro: "price_1RTTLOPSkxSyOwymnX2URZid", Premium: "price_1RTTLkPSkxSyOwymwyO4cVgC")
    - allow_subscription_change: If True (default), cancels existing subscription and creates new one. 
                                If False, rejects the request if user already has active subscription.
    
    Returns either:
    - Success: checkout_url and session_id for Stripe checkout
    - Error: error message with current and requested plan details
    """
    try:
        session_data = await stripe_service.create_checkout_session(
            checkout_data.price_id, 
            current_user.email,
            checkout_data.allow_subscription_change
        )
        
        # Check if we got an error response (subscription rejected)
        if "error" in session_data:
            return CheckoutSessionResponse(
                error=session_data["error"],
                current_plan=session_data.get("current_plan"),
                requested_plan=session_data.get("requested_plan")
            )
        
        # Success case
        return CheckoutSessionResponse(
            checkout_url=session_data["checkout_url"],
            session_id=session_data["session_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook",
    description="Handle Stripe webhook events",
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid payload or signature"}
    })
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """Handle Stripe webhook events for subscription updates."""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        # Get raw body
        body = await request.body()
        
        # Get Stripe service (without user dependency)
        from app.main import app
        stripe_service = StripeService(app.mongodb)
        
        # Process webhook
        result = await stripe_service.handle_webhook(body, stripe_signature)
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me",
    response_model=UserSubscriptionResponse,
    description="Get current user's subscription information"
)
async def get_my_subscription(
    current_user: UserResponse = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
) -> UserSubscriptionResponse:
    """Get the current user's subscription plan and status."""
    try:
        subscription_info = await stripe_service.get_user_subscription_status(current_user.id)
        
        return UserSubscriptionResponse(
            email=current_user.email,
            subscription_plan=subscription_info["subscription_plan"],
            subscription_status=subscription_info["subscription_status"],
            stripe_customer_id=subscription_info["stripe_customer_id"],
            created_at=current_user.created_at,
            last_login=subscription_info.get("last_login")
        )
    except Exception as e:
        logger.error(f"Error getting subscription info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/billing-portal",
    response_model=BillingPortalResponse,
    description="Create a Stripe billing portal session for subscription management",
    responses={
        200: {"description": "Billing portal session created successfully"},
        400: {"description": "No Stripe customer found"},
        401: {"description": "Not authenticated"}
    })
async def create_billing_portal(
    current_user: UserResponse = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
) -> BillingPortalResponse:
    """
    Create a Stripe billing portal session for subscription management.
    
    This allows users to:
    - Update payment methods
    - View billing history
    - Cancel subscriptions
    - Download invoices
    
    Requires the user to have an existing Stripe customer (i.e., have created at least one subscription).
    """
    try:
        portal_data = await stripe_service.create_billing_portal_session(current_user.email)
        return BillingPortalResponse(portal_url=portal_data["portal_url"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating billing portal: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 