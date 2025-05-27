# FastAPI MongoDB Authentication API Overview

Your backend API is a comprehensive authentication system built with FastAPI and MongoDB, providing essential user authentication, account management, chat functionality, and **Stripe subscription management**. Here's what it does:

## Core Functionality

- **User Registration**: Creates new user accounts storing email and securely hashed passwords
- **User Authentication**: Validates credentials and issues access tokens (OAuth2/JWT based)
- **Account Management**: Allows users to view their profile information
- **Chat Streaming**: Provides real-time chat streaming capabilities with message history
- **🆕 Subscription Management**: Complete Stripe integration with multiple subscription tiers

## Security Features

- **Email Verification**: Implements a verification workflow with tokenized email links
- **Password Management**:
  - Password change (for authenticated users)
  - Password reset via email (forgot password flow)
  - Secure token-based password reset mechanism
- **🆕 Subscription Access Control**: Role-based access to features based on subscription tier

## API Endpoints

### Authentication

- `/auth/register`: Creates new user accounts
- `/auth/login`: Authenticates users and issues access tokens
- `/auth/change-password`: Updates authenticated user passwords
- `/auth/verify/{token}`: Verifies email addresses via tokens
- `/auth/resend-verification`: Resends verification emails
- `/auth/forgot-password`: Initiates password reset process
- `/auth/reset-password/{token}`: Completes password reset with token

### User Management

- `/users/me`: Retrieves authenticated user's profile information

### 🆕 Subscription Management

- `/subscription/free`: Free tier page (accessible to all users)
- `/subscription/pro`: Pro tier page (requires Pro or Premium subscription)
- `/subscription/premium`: Premium tier page (requires Premium subscription)
- `/subscription/create-checkout-session`: Create Stripe checkout session for upgrades
- `/subscription/manage-portal`: Get Stripe customer portal URL for self-service
- `/subscription/cancel`: Cancel active subscription directly
- `/subscription/me`: Get current user's subscription information
- `/webhook`: Stripe webhook handler for subscription events

### Chat

- `/chat/`: Create a new chat or list existing chats
- `/chat/{chat_id}`: Get, update, or delete a specific chat
- `/chat/stream`: Stream chat responses in real-time

## 🎯 Subscription Tiers

| Feature          | Free | Pro ($19/month) | Premium ($49/month) |
| ---------------- | ---- | --------------- | ------------------- |
| Basic Chat       | ✅   | ✅              | ✅                  |
| Advanced Chat    | ❌   | ✅              | ✅                  |
| Pro Features     | ❌   | ✅              | ✅                  |
| Premium Features | ❌   | ❌              | ✅                  |

## 🚀 Stripe Setup Guide

### 1. Configure Stripe Dashboard

1. **Get your API keys** from [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. **Create Products & Prices**:
   - Pro Plan: $19/month → `price_1RTTLOPSkxSyOwymnX2URZid`
   - Premium Plan: $49/month → `price_1RTTLkPSkxSyOwymwyO4cVgC`
3. **Configure Customer Portal** at [Portal Settings](https://dashboard.stripe.com/test/settings/billing/portal)
4. **Set up Webhook** pointing to `https://yourdomain.com/webhook`

### 2. Environment Variables

Update your `.env` file:

```env
# MongoDB settings
MONGODB_URL=your_mongodb_url
DATABASE_NAME=your_database_name

# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe Settings
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Email Settings
MAIL_SERVER=your-mail-server
MAIL_PORT=465
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=your-email@example.com
MAIL_FROM_NAME=YourAppName

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Verification Settings
VERIFICATION_TOKEN_EXPIRE_HOURS=24
```

### 3. Subscription Management Examples

#### Create Checkout Session (Upgrade to Pro)

```bash
curl -X POST "http://localhost:8000/subscription/create-checkout-session" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_1RTTLOPSkxSyOwymnX2URZid",
    "allow_subscription_change": true
  }'
```

#### Get Customer Portal URL

```bash
curl -H "Authorization: Bearer <jwt_token>" \
  "http://localhost:8000/subscription/manage-portal"
```

#### Cancel Subscription

```bash
curl -X POST "http://localhost:8000/subscription/cancel" \
  -H "Authorization: Bearer <jwt_token>"
```

#### Check Subscription Status

```bash
curl -H "Authorization: Bearer <jwt_token>" \
  "http://localhost:8000/subscription/me"
```

### 4. Subscription Features

#### Multiple Subscription Prevention

- **Strict Mode**: Rejects new subscriptions if user already has one
- **Auto-Cancel Mode**: Cancels existing subscription before creating new one

#### Self-Service Portal

- Update payment methods
- View billing history
- Cancel subscriptions
- Download invoices

#### Direct Backend Cancellation

- Immediate cancellation through API
- Automatic plan downgrade to "free"
- Database synchronization

## Chat Streaming Features

The chat system provides:

- **Real-time Streaming**: Messages are streamed word-by-word for a responsive experience
- **Chat History**: All conversations are saved and can be retrieved later
- **Chat Management**: Create, list, update, and delete chat conversations
- **Continuation**: Continue existing conversations by providing a chat ID
- **🆕 Subscription-Based Access**: Advanced chat features require Pro+ subscription

## Using the Chat API

### Creating a New Chat

```bash
POST /chat/
Body: { "title": "Optional chat title" }
```

### Streaming a Response

```bash
POST /chat/stream
Body: {
  "message": "Your message here",
  "chat_id": "optional-existing-chat-id"
}
```

The response is a Server-Sent Events (SSE) stream that can be consumed by the frontend.

### Listing Chats

```bash
GET /chat/?skip=0&limit=20
```

### Getting Chat Details

```bash
GET /chat/{chat_id}
```

### Updating Chat Title

```bash
PUT /chat/{chat_id}
Body: { "title": "New chat title" }
```

### Deleting a Chat

```bash
DELETE /chat/{chat_id}
```

## 🔧 Development Setup

1. **Clone the repository**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Set up environment variables** in `.env` file
4. **Configure Stripe** (see Stripe Setup Guide above)
5. **Run the server**: `uvicorn app.main:app --reload`

## 🚀 Production Deployment

- [ ] Replace test Stripe keys with live keys
- [ ] Configure Stripe webhook with production URL
- [ ] Set up Stripe Customer Portal for live mode
- [ ] Configure production MongoDB instance
- [ ] Set up proper email service (SMTP)
- [ ] Configure CORS for production domains

## 📚 Additional Resources

- [Stripe Setup Guide](STRIPE_SETUP.md) - Detailed Stripe configuration
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Stripe API Reference](https://stripe.com/docs/api)

The system includes proper validation, error handling, and rate limiting (for verification emails), following security best practices for user authentication and subscription management workflows.
