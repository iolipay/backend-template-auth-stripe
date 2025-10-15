# FastAPI MongoDB Authentication API Overview

Your backend API is a comprehensive authentication system built with FastAPI and MongoDB, providing essential user authentication, account management, **transaction tracking with currency conversion**, **Telegram bot integration with automated reminders**, chat functionality, and **Stripe subscription management**. Here's what it does:

## Core Functionality

- **User Registration**: Creates new user accounts storing email and securely hashed passwords
- **User Authentication**: Validates credentials and issues access tokens (OAuth2/JWT based)
- **Account Management**: Allows users to view their profile information
- **💰 Income Tracking**: Track income in multiple currencies with automatic conversion to GEL
- **📱 Telegram Integration**: Automated reminders and notifications via Telegram bot
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

### 💰 Income Tracking

**Transaction Management:**
- `POST /transactions/`: Create a new income transaction with auto-conversion to GEL
- `GET /transactions/`: List income transactions (with filtering by date, currency, category)
- `GET /transactions/{id}`: Get a specific transaction
- `PUT /transactions/{id}`: Update a transaction
- `DELETE /transactions/{id}`: Delete a transaction

**Statistics & Analytics:**
- `GET /transactions/stats`: Get overall income statistics (total income, breakdown by category)
- `GET /transactions/stats/monthly`: Get monthly breakdown for the year
- `GET /transactions/stats/current-month`: Get current month stats with projections
- `GET /transactions/stats/chart-data`: Get time-series data for charts (daily/weekly/monthly)

**Currency Information:**
- `GET /transactions/currencies/available`: Get list of supported currencies
- `GET /transactions/currencies/rate`: Get exchange rate for a currency

### Chat

- `/chat/`: Create a new chat or list existing chats
- `/chat/{chat_id}`: Get, update, or delete a specific chat
- `/chat/stream`: Stream chat responses in real-time

### 📱 Telegram Integration

- `/telegram/connect`: Generate connection token and deep link to connect Telegram account
- `/telegram/disconnect`: Disconnect Telegram account
- `/telegram/webhook`: Webhook endpoint for bot updates (called by Telegram)
- `/telegram/status`: Get current Telegram connection status
- `/telegram/settings`: Get/update notification preferences
- `/telegram/test-reminder`: Send test reminder to verify integration
- `/telegram/bot-info`: Get bot information

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
5. **Configure Telegram Bot** (optional - see Telegram Bot Features section)
6. **Create database indexes**: `python -m app.core.database_indexes`
7. **Run the server**: `uvicorn app.main:app --reload`
8. **For Telegram development**: Run `./setup_webhook.sh` to configure ngrok

## 🚀 Production Deployment

- [ ] Replace test Stripe keys with live keys
- [ ] Configure Stripe webhook with production URL
- [ ] Set up Stripe Customer Portal for live mode
- [ ] Configure production MongoDB instance
- [ ] Set up proper email service (SMTP)
- [ ] Configure CORS for production domains
- [ ] **Telegram Bot** (if using):
  - [ ] Set production Telegram webhook URL
  - [ ] Configure `TELEGRAM_BOT_TOKEN` in production env
  - [ ] No ngrok needed in production

## 💰 Income Tracking Features

- **Multi-currency support**: Track income in USD, EUR, GBP, RUB, and 30+ other currencies
- **Automatic conversion**: All amounts automatically converted to GEL using official NBG rates
- **Smart filtering**: Filter by date range, currency, and category
- **Real-time statistics**: Get total income and breakdown by category
- **Historical accuracy**: Uses official exchange rates for the transaction date
- **Efficient caching**: Exchange rates cached for 1 hour to minimize API calls
- **Income categories**: salary, freelance, business, investment, rental_income, dividends, bonus, commission, other

**📊 Advanced Analytics:**
- **Monthly breakdowns**: Get income statistics for each month of the year
- **Current month tracking**: Track current month progress with daily averages and projections
- **Month-over-month comparison**: See percentage change vs previous month
- **Chart-ready data**: Time-series data for daily, weekly, and monthly charts
- **Projected income**: Automatic projection of end-of-month income based on current pace

## 📱 Telegram Bot Features

### Features

- **Automated Reminders**: Daily transaction reminders at user's preferred time
- **Weekly Summaries**: Income/expense overview sent every Monday
- **Monthly Reports**: Detailed financial reports on the 1st of each month
- **Subscription Alerts**: Notifications 14, 7, and 3 days before subscription expires
- **Inactivity Alerts**: Re-engagement messages for inactive users
- **Easy Connection**: One-click deep link to connect Telegram account
- **Customizable Settings**: Control notification preferences and timing
- **Test Reminders**: Test your bot integration with sample reminders
- **Rich Formatting**: HTML-formatted messages with emojis for better readability
- **Smart Error Handling**: Automatic notification disable if user blocks bot

### Quick Setup (5 Minutes)

**Step 1: Create Your Bot**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy your bot token

**Step 2: Configure Environment**
```env
# Add to .env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
```

**Step 3: Local Development Setup**
```bash
# Setup ngrok (one-time)
# Sign up at: https://dashboard.ngrok.com/signup
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Start webhook
./setup_webhook.sh

# Get connection link for testing
./connect_telegram.sh
```

**Step 4: Connect Your Account**
1. Run `./connect_telegram.sh` and login
2. Click the generated link
3. Click "Start" in Telegram
4. Done! 🎉

### Helper Scripts

- `./setup_webhook.sh` - Configures ngrok and Telegram webhook for local development
- `./connect_telegram.sh` - Generates connection link for linking Telegram accounts

**Important:** These are one-time helper scripts that exit after running. They are NOT services that need to stay running.

### What Needs To Stay Running?

For local development with Telegram:

**Terminal 1: Backend (Always Running)**
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2: Setup (Run Once Per Session)**
```bash
./setup_webhook.sh
# This starts ngrok in background and exits
# ngrok stays running, script exits
```

**Terminal 3: Connection Links (Run When Needed)**
```bash
./connect_telegram.sh
# Run this each time a user wants to connect
# Script exits after showing the link
```

Only 2 things stay running: **Backend** + **ngrok** (background process)

### Production Setup

For production, set permanent webhook:
```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://api.yourdomain.com/telegram/webhook"
```

No ngrok needed in production!

### Documentation

- **[Local Setup Guide](TELEGRAM_LOCAL_SETUP.md)** - Complete local development setup
- **[ngrok Setup](NGROK_SETUP.md)** - Detailed ngrok configuration guide
- **[Quick Start](TELEGRAM_QUICKSTART.md)** - 5-minute quick start guide
- **[Integration Guide](TELEGRAM_INTEGRATION_GUIDE.md)** - Complete API reference
- **[Frontend Guide](FRONTEND_TELEGRAM_GUIDE.md)** - React implementation guide
- **[UI Mockups](TELEGRAM_UI_MOCKUPS.md)** - Design specifications

## 📚 Documentation

- **[API Quick Reference](API_QUICK_REFERENCE.md)** ⚡ - Quick reference for all API endpoints with curl examples
- **[Frontend Integration Guide](FRONTEND_INTEGRATION.md)** 💻 - Complete React integration examples and components
- **[Transaction Management Guide](TRANSACTIONS_GUIDE.md)** 💰 - Detailed transaction API documentation
- **[Charts & Statistics Guide](CHARTS_AND_STATS_GUIDE.md)** 📊 - Analytics and chart data endpoints
- **[Telegram Integration Guide](TELEGRAM_INTEGRATION_GUIDE.md)** 📱 - Complete Telegram bot setup and usage guide
- **[Stripe Setup Guide](STRIPE_SETUP.md)** 💳 - Stripe configuration and subscription management
- **[Architecture Guide](CLAUDE.md)** 🏗️ - System architecture and development guide

## 🔗 External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework docs
- [Stripe API Reference](https://stripe.com/docs/api) - Stripe integration docs
- [National Bank of Georgia API](https://nbg.gov.ge/en/monetary-policy/currency) - Official exchange rates

The system includes proper validation, error handling, and rate limiting (for verification emails), following security best practices for user authentication, transaction management, and subscription workflows.
