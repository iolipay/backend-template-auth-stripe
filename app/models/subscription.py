from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Subscription(BaseModel):
    user_id: str
    plan_id: str
    status: str
    current_period_end: datetime
    stripe_subscription_id: str 