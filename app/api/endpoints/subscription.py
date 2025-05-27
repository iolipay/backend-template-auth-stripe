from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from app.api.deps import get_current_user, get_stripe_service
from app.schemas.user import UserResponse
from app.schemas.subscription import CheckoutSessionCreate, CheckoutSessionResponse, UserSubscriptionResponse
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
        200: {"description": "Checkout session created successfully"},
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
    
    Use your Stripe Price IDs:
    - Pro Plan ($19/month): "price_your_pro_price_id"
    - Premium Plan ($49/month): "price_your_premium_price_id"
    """
    try:
        session_data = await stripe_service.create_checkout_session(
            checkout_data.price_id, 
            current_user.email
        )
        return CheckoutSessionResponse(**session_data)
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