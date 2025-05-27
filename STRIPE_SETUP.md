# Enhanced Stripe Subscription Management

## 🎯 What You Have Now

### Core Subscription Pages

- `GET /subscription/free` → `{"message": "free page"}` (accessible to all)
- `GET /subscription/pro` → `{"message": "pro page"}` (requires Pro plan)
- `GET /subscription/premium` → `{"message": "premium page"}` (requires Premium plan)

### 🆕 Advanced Subscription Management

- `POST /subscription/create-checkout-session` - **Enhanced with multiple subscription prevention**
- `POST /subscription/billing-portal` - **NEW**: Stripe customer portal for self-service
- `POST /webhook` - Direct webhook endpoint for Stripe
- `GET /subscription/me` - Check user's current plan

## 🚀 New Features

### 1. Multiple Subscription Prevention

The system now prevents users from having multiple active subscriptions. You have two options:

#### Option A: Reject New Subscriptions (Strict Mode)

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1RTTLkPSkxSyOwymwyO4cVgC",
    "allow_subscription_change": false
  }'
```

**Response when user already has subscription:**

```json
{
  "error": "You already have an active pro subscription. Please cancel your current subscription before creating a new one.",
  "current_plan": "pro",
  "requested_plan": "premium"
}
```

#### Option B: Auto-Cancel & Upgrade (Default)

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1RTTLkPSkxSyOwymwyO4cVgC",
    "allow_subscription_change": true
  }'
```

**Response:**

```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_..."
}
```

> **Note:** This automatically cancels the existing subscription and creates a new checkout session.

### 2. Stripe Billing Portal Integration

Allow users to manage their subscriptions through Stripe's native interface:

```bash
curl -X POST "http://localhost:8000/subscription/billing-portal" \
  -H "Authorization: Bearer <jwt_token>"
```

**Response:**

```json
{
  "portal_url": "https://billing.stripe.com/session/..."
}
```

**Features available in billing portal:**

- ✅ Update payment methods
- ✅ View billing history & invoices
- ✅ Cancel subscriptions
- ✅ Download receipts
- ✅ Pause/resume subscriptions (if configured)

## 📋 Complete Setup Guide

### 1. ✅ Price IDs Already Configured!

- **Pro Plan ($19/month)**: `price_1RTTLOPSkxSyOwymnX2URZid`
- **Premium Plan ($49/month)**: `price_1RTTLkPSkxSyOwymwyO4cVgC`

### 2. Configure Stripe Webhook

1. Go to **Stripe Dashboard** → **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Set URL: `https://your-domain.com/webhook`
4. Select events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy **Webhook Secret** to `.env`

### 3. Environment Variables

```env
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
FRONTEND_URL=http://localhost:3000
```

## 🧪 Complete Test Scenarios

### Scenario 1: Free User Upgrades to Pro

```bash
# 1. Check current plan (should be "free")
curl -H "Authorization: Bearer <jwt>" "http://localhost:8000/subscription/me"

# 2. Try accessing pro page (should get 403)
curl -H "Authorization: Bearer <jwt>" "http://localhost:8000/subscription/pro"

# 3. Create checkout session for Pro
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_1RTTLOPSkxSyOwymnX2URZid"}'

# 4. Complete payment in Stripe checkout
# 5. Webhook automatically updates user plan
# 6. Try pro page again (should work now)
```

### Scenario 2: Pro User Tries to Subscribe to Premium (Reject Mode)

```bash
# 1. User already has Pro subscription
curl -H "Authorization: Bearer <jwt>" "http://localhost:8000/subscription/me"

# 2. Try to subscribe to Premium with strict mode
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1RTTLkPSkxSyOwymwyO4cVgC",
    "allow_subscription_change": false
  }'

# Expected: Error response with current and requested plan info
```

### Scenario 3: Pro User Upgrades to Premium (Auto-Cancel Mode)

```bash
# 1. Create checkout session with auto-cancel
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1RTTLkPSkxSyOwymwyO4cVgC",
    "allow_subscription_change": true
  }'

# 2. System automatically cancels Pro subscription
# 3. Creates new checkout for Premium
# 4. User completes payment
# 5. Now has Premium access
```

### Scenario 4: User Manages Subscription via Billing Portal

```bash
# 1. Create billing portal session
curl -X POST "http://localhost:8000/subscription/billing-portal" \
  -H "Authorization: Bearer <jwt>"

# 2. Redirect user to the portal_url
# 3. User can cancel, update payment methods, etc.
# 4. Changes are automatically synced via webhooks
```

## 🎯 API Response Examples

### Successful Checkout Session

```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

### Rejected Subscription (Already Has Active)

```json
{
  "error": "You already have an active pro subscription. Please cancel your current subscription before creating a new one.",
  "current_plan": "pro",
  "requested_plan": "premium"
}
```

### User Subscription Status

```json
{
  "email": "user@example.com",
  "subscription_plan": "pro",
  "subscription_status": "active",
  "stripe_customer_id": "cus_...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

## 🔧 Advanced Configuration Options

### Customize Subscription Change Behavior

You can modify the default behavior in `app/services/stripe.py`:

```python
# Default: allow_subscription_change=True (auto-cancel)
# Change to: allow_subscription_change=False (reject) for stricter control
```

### Add More Webhook Events

In your Stripe webhook configuration, you can add:

- `customer.subscription.trial_will_end`
- `invoice.payment_failed`
- `customer.subscription.paused`

### Custom Success/Cancel URLs

Update in `app/services/stripe.py`:

```python
success_url=f"{settings.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}"
cancel_url=f"{settings.FRONTEND_URL}/pricing"
```

## 🚀 Production Checklist

- [ ] Replace test Stripe keys with live keys
- [ ] Update webhook endpoint URL to production domain
- [ ] Configure Stripe webhook with live endpoint
- [ ] Test all subscription flows in Stripe test mode first
- [ ] Set up monitoring for webhook failures
- [ ] Configure billing portal settings in Stripe dashboard
- [ ] Test subscription change scenarios thoroughly
- [ ] Set up alerts for failed payments

That's it! Your subscription system now handles multiple subscription prevention and provides users with full self-service capabilities. 🎉
