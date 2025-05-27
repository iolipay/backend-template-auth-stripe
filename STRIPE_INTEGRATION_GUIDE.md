# Stripe Integration Guide

This guide explains how to set up and use the Stripe integration for subscription management.

## 🚀 Quick Setup

### 1. Environment Variables

Add the following to your `.env` file:

```env
# Stripe Settings
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_PUBLIC_KEY=pk_test_your-stripe-public-key
STRIPE_WEBHOOK_SECRET=whsec_your-stripe-webhook-secret
FRONTEND_URL=http://localhost:3000
```

### 2. Create Stripe Products and Prices

In your Stripe Dashboard, create:

1. **Pro Plan** - Monthly/Yearly pricing
2. **Premium Plan** - Monthly/Yearly pricing

Note down the Price IDs for your frontend integration.

### 3. Configure Webhooks

In Stripe Dashboard, create a webhook endpoint pointing to:

```
https://your-domain.com/subscription/webhook
```

Select these events:

- `checkout.session.completed`
- `invoice.payment_succeeded`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## 📊 User Subscription Levels

### Free Plan (Default)

- Basic chat functionality
- Limited API calls (100/day)
- Basic features

### Pro Plan

- Advanced chat features
- Increased limits (1,000 API calls/day)
- Priority support
- File uploads

### Premium Plan

- All Pro features
- Highest limits (10,000 API calls/day)
- Custom models
- API access
- Team collaboration

## 🔗 API Endpoints

### Create Checkout Session

```http
POST /subscription/create-checkout-session
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "price_id": "price_1234567890"
}
```

**Response:**

```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_...",
  "session_id": "cs_1234567890"
}
```

### Get User Subscription Status

```http
GET /subscription/me
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "email": "user@example.com",
  "subscription_plan": "pro",
  "subscription_status": "active",
  "stripe_customer_id": "cus_1234567890",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

### Webhook Endpoint

```http
POST /subscription/webhook
Stripe-Signature: <stripe_signature>
```

This endpoint automatically handles:

- ✅ Payment completions
- ✅ Subscription updates
- ✅ Cancellations
- ✅ Failed payments

## 🛡️ Access Control

### Using Decorators

```python
from app.core.subscription import require_subscription, SubscriptionLevel

@require_subscription(SubscriptionLevel.PRO)
async def premium_feature():
    return {"message": "This is a Pro feature"}
```

### Feature-based Access Control

```python
from app.core.subscription import require_feature

@require_feature("advanced_chat")
async def advanced_chat_endpoint():
    return {"message": "Advanced chat feature"}
```

### Manual Access Checks

```python
from app.core.subscription import check_feature_access, SubscriptionLevel

def some_function(user: UserResponse):
    check_feature_access(user, SubscriptionLevel.PRO, "premium feature")
    # Feature logic here
```

## 💾 Database Schema

### User Document Structure

```json
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "hashed_password": "...",
  "stripe_customer_id": "cus_1234567890",
  "subscription_plan": "pro",
  "subscription_status": "active",
  "subscription_end_date": "2024-02-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

## 🔄 Frontend Integration Example

### 1. Create Checkout Session

```javascript
const createCheckoutSession = async (priceId) => {
  const response = await fetch("/subscription/create-checkout-session", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ price_id: priceId }),
  });

  const data = await response.json();
  window.location.href = data.checkout_url;
};
```

### 2. Check User Subscription

```javascript
const getUserSubscription = async () => {
  const response = await fetch("/subscription/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return await response.json();
};
```

## 🎯 Usage Limits

The system includes built-in usage tracking:

```python
from app.core.subscription import check_usage_limit

# Before processing API request
check_usage_limit(user, "api_calls_per_day", current_usage)
```

### Limits by Plan:

| Feature            | Free | Pro   | Premium |
| ------------------ | ---- | ----- | ------- |
| API Calls/Day      | 100  | 1,000 | 10,000  |
| Chat Messages/Day  | 50   | 500   | 5,000   |
| File Uploads/Month | 5    | 50    | 500     |
| Max File Size (MB) | 10   | 100   | 1,000   |

## 🔧 Customization

### Adding New Subscription Plans

1. **Update SubscriptionLevel class:**

```python
class SubscriptionLevel:
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"  # New plan
```

2. **Update hierarchy:**

```python
SUBSCRIPTION_HIERARCHY = {
    SubscriptionLevel.FREE: 0,
    SubscriptionLevel.PRO: 1,
    SubscriptionLevel.PREMIUM: 2,
    SubscriptionLevel.ENTERPRISE: 3  # New plan
}
```

3. **Add usage limits:**

```python
USAGE_LIMITS = {
    # ... existing limits
    SubscriptionLevel.ENTERPRISE: {
        "api_calls_per_day": 100000,
        "chat_messages_per_day": 50000,
        # ... other limits
    }
}
```

### Custom Price ID Mapping

Update the `_get_plan_name_from_price_id` method in `StripeService`:

```python
async def _get_plan_name_from_price_id(self, price_id: str) -> str:
    price_to_plan = {
        "price_1ABC123": "pro",
        "price_1DEF456": "premium",
        "price_1GHI789": "enterprise",  # Your actual Stripe Price IDs
    }
    return price_to_plan.get(price_id, "pro")
```

## 🧪 Testing

### Test User Registration (Free Plan)

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Test Subscription Upgrade

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1234567890"
  }'
```

### Test Protected Endpoints

```bash
# Should work for all users
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Authorization: Bearer <jwt_token>"

# Should require Pro+ subscription
curl -X POST "http://localhost:8000/chat/stream/advanced" \
  -H "Authorization: Bearer <jwt_token>"
```

## 🚨 Error Handling

The API returns appropriate HTTP status codes:

- `401` - Not authenticated
- `403` - Insufficient subscription level
- `429` - Usage limits exceeded
- `400` - Invalid Stripe data
- `500` - Server error

Example error response:

```json
{
  "detail": "Access to advanced chat requires a pro subscription or higher. Your current plan: free"
}
```

## 📈 Monitoring

The system logs important events:

- Subscription creation
- Plan upgrades/downgrades
- Failed payments
- Usage limit violations

Check application logs for Stripe webhook events and subscription changes.

---

## 🎉 You're Ready!

Your Stripe integration is now complete with:

- ✅ Subscription checkout
- ✅ Webhook handling
- ✅ Access control
- ✅ Usage limits
- ✅ Free plan onboarding
- ✅ MongoDB integration

Users can register for free and upgrade to paid plans seamlessly!
