from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CheckoutSessionCreate(BaseModel):
    price_id: str
    allow_subscription_change: bool = True  # If True, cancels existing; if False, rejects

class CheckoutSessionResponse(BaseModel):
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    # Error fields for when subscription creation is rejected
    error: Optional[str] = None
    current_plan: Optional[str] = None
    requested_plan: Optional[str] = None

class BillingPortalResponse(BaseModel):
    portal_url: str

class UserSubscriptionResponse(BaseModel):
    email: str
    subscription_plan: str
    subscription_status: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

class WebhookEvent(BaseModel):
    type: str
    data: dict 