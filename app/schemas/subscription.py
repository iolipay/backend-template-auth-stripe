from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CheckoutSessionCreate(BaseModel):
    price_id: str

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str

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