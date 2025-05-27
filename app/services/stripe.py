import stripe
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from app.core.config import settings
from app.core.exceptions import UserNotFoundError
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self, db):
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_checkout_session(self, price_id: str, user_email: str, allow_subscription_change: bool = True) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for subscription.
        
        Args:
            price_id: Stripe Price ID for the subscription
            user_email: User's email address
            allow_subscription_change: If True, cancels existing subscription; if False, rejects new subscription
            
        Returns:
            Dict with checkout_url and session_id, or error message
        """
        try:
            logger.info(f"Creating checkout session for {user_email} with price_id {price_id}")
            
            # Get or create Stripe customer
            customer = await self._get_or_create_customer(user_email)
            logger.info(f"Got customer: {customer.id}")
            
            # Check for existing active subscriptions
            logger.info(f"Checking for existing subscriptions for customer {customer.id}")
            existing_subscriptions = stripe.Subscription.list(
                customer=customer.id,
                status="active",
                limit=10  # Check multiple in case there are any
            )
            
            logger.info(f"Found {len(existing_subscriptions.data)} active subscriptions for customer {customer.id}")
            
            if existing_subscriptions.data:
                # Get the current subscription plan name
                current_subscription = existing_subscriptions.data[0]
                logger.info(f"Current subscription: {current_subscription.id}")
                
                # Get price ID safely
                try:
                    current_price_id = current_subscription.items.data[0].price.id
                    logger.info(f"Current price ID: {current_price_id}")
                    current_plan = await self._get_plan_name_from_price_id(current_price_id)
                    logger.info(f"Current plan: {current_plan}")
                except Exception as e:
                    logger.error(f"Error getting current price ID: {e}")
                    current_plan = "unknown"
                
                # Get the new plan name
                try:
                    new_plan = await self._get_plan_name_from_price_id(price_id)
                    logger.info(f"Requested plan: {new_plan}")
                except Exception as e:
                    logger.error(f"Error getting new plan name: {e}")
                    new_plan = "unknown"
                
                if not allow_subscription_change:
                    # Option 1: Reject new subscription
                    logger.info(f"Rejecting subscription change from {current_plan} to {new_plan}")
                    return {
                        "error": f"You already have an active {current_plan} subscription. Please cancel your current subscription before creating a new one.",
                        "current_plan": current_plan,
                        "requested_plan": new_plan
                    }
                else:
                    # Option 2: Cancel existing subscription(s) first
                    logger.info(f"Canceling existing subscription(s) for customer {customer.id}")
                    
                    for subscription in existing_subscriptions.data:
                        try:
                            # Cancel immediately (not at period end)
                            stripe.Subscription.delete(subscription.id)
                            logger.info(f"Canceled subscription {subscription.id} for customer {customer.id}")
                            
                            # Update user in database
                            await self.db.users.update_one(
                                {"stripe_customer_id": customer.id},
                                {
                                    "$set": {
                                        "subscription_plan": "free",
                                        "subscription_status": "canceled"
                                    }
                                }
                            )
                        except stripe.error.StripeError as e:
                            logger.error(f"Error canceling subscription {subscription.id}: {e}")
                            # Continue with checkout creation even if cancellation fails
            
            # Create checkout session
            logger.info(f"Creating Stripe checkout session for customer {customer.id}")
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{settings.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/pricing",
                metadata={
                    'user_email': user_email,
                    'price_id': price_id
                }
            )
            
            logger.info(f"Successfully created checkout session: {session.id}")
            return {
                'checkout_url': session.url,
                'session_id': session.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_or_create_customer(self, email: str) -> stripe.Customer:
        """Get existing Stripe customer or create new one"""
        # First check if customer exists in our database
        user = await self.db.users.find_one({"email": email})
        if user and user.get("stripe_customer_id"):
            try:
                # Verify customer exists in Stripe
                customer = stripe.Customer.retrieve(user["stripe_customer_id"])
                return customer
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist in Stripe, create new one
                pass
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            metadata={'source': 'api'}
        )
        
        # Update user with customer ID
        await self.db.users.update_one(
            {"email": email},
            {"$set": {"stripe_customer_id": customer.id}}
        )
        
        return customer

    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            await self._handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            await self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            await self._handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            await self._handle_subscription_deleted(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return {"status": "success"}

    async def _handle_checkout_completed(self, session: Dict[str, Any]):
        """Handle successful checkout completion"""
        try:
            customer_email = session.get('customer_details', {}).get('email')
            if not customer_email:
                customer_email = session['metadata'].get('user_email')
            
            if not customer_email:
                logger.error("No customer email found in checkout session")
                return

            # Get subscription details
            subscription_id = session.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                plan_name = await self._get_plan_name_from_price_id(subscription.items.data[0].price.id)
                
                # Update user subscription
                await self.db.users.update_one(
                    {"email": customer_email},
                    {
                        "$set": {
                            "stripe_customer_id": session['customer'],
                            "subscription_plan": plan_name,
                            "subscription_status": "active",
                            "subscription_end_date": datetime.fromtimestamp(
                                subscription.current_period_end, timezone.utc
                            )
                        }
                    }
                )
                
                logger.info(f"Updated subscription for {customer_email} to {plan_name}")
                
        except Exception as e:
            logger.error(f"Error handling checkout completed: {e}")

    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Handle successful payment"""
        try:
            subscription_id = invoice.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer = stripe.Customer.retrieve(subscription.customer)
                
                # Update subscription end date
                await self.db.users.update_one(
                    {"stripe_customer_id": customer.id},
                    {
                        "$set": {
                            "subscription_status": "active",
                            "subscription_end_date": datetime.fromtimestamp(
                                subscription.current_period_end, timezone.utc
                            )
                        }
                    }
                )
                
                logger.info(f"Updated subscription end date for customer {customer.id}")
                
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {e}")

    async def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle subscription updates"""
        try:
            customer = stripe.Customer.retrieve(subscription['customer'])
            plan_name = await self._get_plan_name_from_price_id(subscription['items']['data'][0]['price']['id'])
            
            await self.db.users.update_one(
                {"stripe_customer_id": customer.id},
                {
                    "$set": {
                        "subscription_plan": plan_name,
                        "subscription_status": subscription['status'],
                        "subscription_end_date": datetime.fromtimestamp(
                            subscription['current_period_end'], timezone.utc
                        )
                    }
                }
            )
            
            logger.info(f"Updated subscription for customer {customer.id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")

    async def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Handle subscription cancellation"""
        try:
            customer = stripe.Customer.retrieve(subscription['customer'])
            
            await self.db.users.update_one(
                {"stripe_customer_id": customer.id},
                {
                    "$set": {
                        "subscription_plan": "free",
                        "subscription_status": "canceled",
                        "subscription_end_date": None
                    }
                }
            )
            
            logger.info(f"Canceled subscription for customer {customer.id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")

    async def _get_plan_name_from_price_id(self, price_id: str) -> str:
        """Map Stripe price ID to plan name"""
        # Replace these with your actual Stripe Price IDs from your dashboard
        price_to_plan = {
            # TODO: Replace with your actual Price IDs from Stripe Dashboard
            "price_1RTTLOPSkxSyOwymnX2URZid": "pro",      # $19/month Pro plan
            "price_1RTTLkPSkxSyOwymwyO4cVgC": "premium",  # $49/month Premium plan
        }
        
        try:
            # Get price details from Stripe to determine plan
            price = stripe.Price.retrieve(price_id)
            
            # You can also check the price nickname or metadata
            if price.nickname:
                if "pro" in price.nickname.lower():
                    return "pro"
                elif "premium" in price.nickname.lower():
                    return "premium"
            
            # Fallback to direct mapping
            return price_to_plan.get(price_id, "pro")
            
        except Exception as e:
            logger.error(f"Error getting plan name for price {price_id}: {e}")
            return "pro"  # Default fallback

    async def get_user_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription status"""
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise UserNotFoundError()
            
            subscription_info = {
                "subscription_plan": user.get("subscription_plan", "free"),
                "subscription_status": user.get("subscription_status"),
                "subscription_end_date": user.get("subscription_end_date"),
                "stripe_customer_id": user.get("stripe_customer_id")
            }
            
            # If user has active subscription, verify with Stripe
            if user.get("stripe_customer_id") and user.get("subscription_status") == "active":
                try:
                    customer = stripe.Customer.retrieve(user["stripe_customer_id"])
                    subscriptions = stripe.Subscription.list(customer=customer.id, status="active")
                    
                    if subscriptions.data:
                        subscription = subscriptions.data[0]
                        subscription_info.update({
                            "subscription_status": subscription.status,
                            "subscription_end_date": datetime.fromtimestamp(
                                subscription.current_period_end, timezone.utc
                            )
                        })
                    else:
                        # No active subscription found, update user
                        subscription_info.update({
                            "subscription_plan": "free",
                            "subscription_status": None
                        })
                        await self.db.users.update_one(
                            {"_id": ObjectId(user_id)},
                            {"$set": {"subscription_plan": "free", "subscription_status": None}}
                        )
                        
                except stripe.error.StripeError:
                    # Handle Stripe API errors gracefully
                    pass
            
            return subscription_info
            
        except Exception as e:
            logger.error(f"Error getting subscription status for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving subscription status")

    async def create_billing_portal_session(self, user_email: str) -> Dict[str, Any]:
        """Create a Stripe billing portal session for subscription management"""
        try:
            # Get user's Stripe customer ID
            user = await self.db.users.find_one({"email": user_email})
            if not user or not user.get("stripe_customer_id"):
                raise HTTPException(
                    status_code=400, 
                    detail="No active Stripe customer found. Please create a subscription first."
                )
            
            # Create billing portal session
            session = stripe.billing_portal.Session.create(
                customer=user["stripe_customer_id"],
                return_url=f"{settings.FRONTEND_URL}/dashboard"
            )
            
            return {
                "portal_url": session.url
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating billing portal session: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating billing portal session: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def cancel_user_subscription(self, user_email: str) -> Dict[str, Any]:
        """Cancel a user's active subscription"""
        try:
            logger.info(f"Attempting to cancel subscription for user: {user_email}")
            
            # Get user's Stripe customer ID
            user = await self.db.users.find_one({"email": user_email})
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if not user.get("stripe_customer_id"):
                raise HTTPException(
                    status_code=400, 
                    detail="No Stripe customer found. User has no subscription to cancel."
                )
            
            customer_id = user["stripe_customer_id"]
            logger.info(f"Found customer ID: {customer_id}")
            
            # Get active subscriptions
            active_subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="active",
                limit=10
            )
            
            if not active_subscriptions.data:
                # Check if user already has free plan in database
                if user.get("subscription_plan") == "free":
                    return {
                        "message": "No active subscription found. User is already on free plan.",
                        "subscription_plan": "free"
                    }
                else:
                    # Update database to reflect reality
                    await self.db.users.update_one(
                        {"email": user_email},
                        {
                            "$set": {
                                "subscription_plan": "free",
                                "subscription_status": None,
                                "subscription_end_date": None
                            }
                        }
                    )
                    return {
                        "message": "No active subscription found. Plan updated to free.",
                        "subscription_plan": "free"
                    }
            
            # Cancel all active subscriptions (should only be one, but just in case)
            canceled_subscriptions = []
            for subscription in active_subscriptions.data:
                try:
                    logger.info(f"Canceling subscription: {subscription.id}")
                    
                    # Cancel the subscription immediately
                    canceled_subscription = stripe.Subscription.delete(subscription.id)
                    canceled_subscriptions.append(canceled_subscription.id)
                    
                    logger.info(f"Successfully canceled subscription: {subscription.id}")
                    
                except stripe.error.StripeError as e:
                    logger.error(f"Error canceling subscription {subscription.id}: {e}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to cancel subscription: {str(e)}"
                    )
            
            # Update user's plan in database
            await self.db.users.update_one(
                {"email": user_email},
                {
                    "$set": {
                        "subscription_plan": "free",
                        "subscription_status": "canceled",
                        "subscription_end_date": None
                    }
                }
            )
            
            logger.info(f"Updated user {user_email} to free plan after cancellation")
            
            return {
                "message": "Subscription cancelled and plan downgraded to free.",
                "subscription_plan": "free",
                "canceled_subscriptions": canceled_subscriptions
            }
            
        except HTTPException:
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Internal server error") 