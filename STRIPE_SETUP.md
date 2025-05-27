# Simple Stripe Setup Guide

## 🎯 What You Have Now

Three simple endpoints:

- `GET /subscription/free` → `{"message": "free page"}` (accessible to all)
- `GET /subscription/pro` → `{"message": "pro page"}` (requires Pro plan)
- `GET /subscription/premium` → `{"message": "premium page"}` (requires Premium plan)

Plus the essential Stripe functionality:

- `POST /subscription/create-checkout-session` (to upgrade users)
- `POST /webhook` ⚡ **Direct webhook endpoint for Stripe**
- `GET /subscription/me` (to check user's plan)

## 📋 Quick Setup Steps

### 1. ✅ Price IDs Already Configured!

You've already added your Stripe Price IDs:

- **Pro Plan ($19/month)**: `price_1RTTLOPSkxSyOwymnX2URZid`
- **Premium Plan ($49/month)**: `price_1RTTLkPSkxSyOwymwyO4cVgC`

### 2. Configure Stripe Webhook

1. Go to your Stripe Dashboard
2. Navigate to **Developers** → **Webhooks**
3. Click **Add endpoint**
4. Set endpoint URL to: `https://your-domain.com/webhook`
   (or `http://localhost:8000/webhook` for testing)
5. Select these events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
6. Copy the **Webhook Secret** to your `.env` file

### 3. Test the Endpoints

```bash
# Test free page (should work for everyone)
curl "http://localhost:8000/subscription/free"

# Test pro page (requires Pro subscription)
curl -H "Authorization: Bearer <jwt_token>" "http://localhost:8000/subscription/pro"

# Test premium page (requires Premium subscription)
curl -H "Authorization: Bearer <jwt_token>" "http://localhost:8000/subscription/premium"
```

### 4. Create Checkout Sessions

To upgrade a user to **Pro ($19/month)**:

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_1RTTLOPSkxSyOwymnX2URZid"}'
```

To upgrade a user to **Premium ($49/month)**:

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_1RTTLkPSkxSyOwymwyO4cVgC"}'
```

## 🔧 Environment Variables

Make sure your `.env` has:

```env
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret  # Get this from webhook settings
FRONTEND_URL=http://localhost:3000
```

## 🎯 User Flow

1. **Free users**: Can access `/subscription/free`
2. **Upgrade**: Use `/subscription/create-checkout-session` with price_id
3. **Payment**: User completes Stripe checkout
4. **Webhook**: Stripe calls `/webhook` → user plan gets updated automatically
5. **Access**: Now can access `/subscription/pro` or `/subscription/premium`

## 🧪 Quick Test Flow

1. Register a user:

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

2. Login to get JWT token:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test@example.com", "password": "password123"}'
```

3. Check current plan (should be "free"):

```bash
curl -H "Authorization: Bearer <jwt_token>" "http://localhost:8000/subscription/me"
```

4. Try pro page (should get 403 error):

```bash
curl -H "Authorization: Bearer <jwt_token>" "http://localhost:8000/subscription/pro"
```

5. Create checkout session:

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_1RTTLOPSkxSyOwymnX2URZid"}'
```

6. Complete payment in Stripe checkout
7. Webhook updates user plan automatically
8. Try pro page again (should work now!)

That's it! Your webhook should now work correctly. 🚀
