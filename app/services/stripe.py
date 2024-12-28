from typing import Optional
from app.models.subscription import Subscription

class StripeService:
    async def create_subscription(self, user_id: str, plan_id: str) -> Optional[Subscription]:
        # TODO: Implement Stripe subscription creation
        pass

    async def handle_webhook(self, payload: dict):
        # TODO: Implement Stripe webhook handling
        pass 