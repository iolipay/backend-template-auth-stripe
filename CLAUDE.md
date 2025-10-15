# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend template with MongoDB, JWT authentication, email verification, Stripe subscription management, transaction tracking with automatic currency conversion, Telegram bot integration with automated reminders, and chat functionality. This is a production-ready authentication system designed to be used as a foundation for SaaS applications with tiered subscription access.

## Development Commands

### Running the Application
```bash
uvicorn app.main:app --reload
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Creating Database Indexes
```bash
python -m app.core.database_indexes
```

## Architecture

### Application Structure

The codebase follows a clean architecture pattern with clear separation of concerns:

- **app/main.py**: Application entry point, router registration, CORS configuration, MongoDB lifecycle management
- **app/core/**: Core utilities and configuration
  - `config.py`: Pydantic settings with environment variable loading
  - `security.py`: JWT token creation, password hashing/verification (bcrypt), password validation
  - `subscription.py`: Subscription hierarchy, access control decorators, usage limits, and feature flags
  - `exceptions.py`: Custom HTTP exceptions
- **app/api/**: API layer
  - `endpoints/`: Route handlers for auth, users, chat, subscription, transactions, telegram
  - `deps.py`: Dependency injection (get_current_user, service providers)
- **app/services/**: Business logic layer
  - `auth.py`: User authentication, registration, password management, email verification
  - `email.py`: Email sending via fastapi-mail (verification, password reset)
  - `stripe.py`: Stripe integration for subscriptions, webhooks, customer management
  - `chat.py`: Chat functionality with streaming support
  - `transaction.py`: Transaction management with filtering, statistics
  - `currency.py`: Currency conversion using National Bank of Georgia API with caching
  - `telegram.py`: Telegram Bot API integration for sending messages and managing connections
  - `scheduler.py`: APScheduler-based reminder scheduler for automated notifications
- **app/models/**: Pydantic models for database documents
- **app/schemas/**: Pydantic models for API request/response validation

### Database Architecture

MongoDB collections:
- **users**: User documents with authentication, verification, subscription, and Telegram fields
  - Key fields: `email`, `hashed_password`, `is_verified`, `verification_token`, `stripe_customer_id`, `subscription_plan`, `subscription_status`
  - Telegram fields: `telegram_chat_id`, `telegram_username`, `telegram_connected_at`, `telegram_notifications_enabled`, `telegram_reminder_time`, `telegram_connection_token`, `telegram_connection_token_expires`
  - Plans: "free" (default), "pro", "premium"
- **transactions**: Financial transaction records with currency conversion
  - Key fields: `user_id`, `amount`, `currency`, `amount_gel`, `exchange_rate`, `transaction_date`, `type` (income/expense), `category`, `description`
  - All transactions stored with both original currency and GEL conversion
  - Indexed by user_id + transaction_date for efficient queries
- **chats**: Chat conversation documents
- **Subscriptions managed by Stripe**: Subscription state synchronized via webhooks

### Subscription System Architecture

**Three-tier system** with hierarchical access:
- Free tier (rank 0): Basic access
- Pro tier (rank 1): Includes all Free features + Pro features
- Premium tier (rank 2): Includes all Pro features + Premium features

**Access Control Mechanisms**:
1. **Decorator-based**: `@require_subscription(SubscriptionLevel.PRO)` on endpoints
2. **Feature-based**: `@require_feature("advanced_chat")` for specific features
3. **Programmatic**: `check_feature_access()` and `has_access()` functions
4. **Usage limits**: `check_usage_limit()` for rate limiting by tier

**Stripe Integration**:
- Checkout sessions created via `/subscription/create-checkout-session`
- Multiple subscription prevention: `allow_subscription_change` parameter controls whether to reject or auto-cancel existing subscriptions
- Webhook handling at `/webhook` for subscription lifecycle events
- Customer portal integration for self-service management
- Direct cancellation endpoint with automatic downgrade to free tier

**Subscription State Management**:
- User subscription plan stored in MongoDB `users` collection
- Stripe customer ID links users to Stripe customers
- Webhooks sync Stripe subscription events to MongoDB
- Subscription status updated on: checkout completion, payment success, subscription updates/deletions

### Authentication Flow

1. **Registration** → User created with `is_verified=False` → Verification email sent with token
2. **Email Verification** → Token validated → User marked as verified
3. **Login** → Credentials validated → JWT access token issued (OAuth2 Bearer)
4. **Protected Routes** → Token extracted → User authenticated via dependency injection (`get_current_user`)
5. **Password Reset** → Forgot password → Email with reset token → Reset with new password

**Security Features**:
- Password requirements: ≥8 chars, ≥1 letter, ≥1 digit
- Bcrypt hashing with 12 rounds
- JWT tokens with configurable expiration
- Email verification rate limiting (prevents spam)
- Secure token-based password reset

### Stripe Price IDs

Hardcoded in the codebase (test mode):
- **Pro Plan**: `price_1RTTLOPSkxSyOwymnX2URZid` ($19/month)
- **Premium Plan**: `price_1RTTLkPSkxSyOwymwyO4cVgC` ($49/month)

These must be updated in the Stripe dashboard and service code for production.

### Transaction System Architecture

**Currency Conversion Flow**:
1. User creates transaction in any currency (USD, EUR, GEL, etc.)
2. System fetches exchange rate from National Bank of Georgia API for the transaction date
3. Amount automatically converted to GEL using official rate
4. Both original and converted amounts stored in database
5. Exchange rates cached for 1 hour to minimize API calls

**Transaction Features**:
- **Multi-currency support**: Supports all currencies from NBG API (USD, EUR, GBP, RUB, etc.)
- **Automatic conversion**: All amounts converted to GEL for standardized reporting
- **Filtering**: By date range, currency, type (income/expense), category
- **Statistics**: Total income, expenses, balance, breakdown by category (all in GEL)
- **Categories**: Predefined categories for income (salary, freelance, business) and expenses (food, rent, utilities, etc.)

**NBG API Integration**:
- Endpoint: `https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date=YYYY-MM-DD`
- Returns exchange rates for ~30 currencies
- Rates are per currency unit (adjusted for quantity, e.g., JPY quoted per 100 units)
- Singleton service pattern with in-memory caching
- GEL to GEL always returns rate of 1.0

### Telegram Integration Architecture

**Purpose**: Automated reminders and notifications via Telegram bot

**User Connection Flow**:
1. User requests connection via `POST /telegram/connect`
2. Backend generates secure token and Telegram deep link
3. User clicks deep link → Opens bot in Telegram → Clicks "Start"
4. Bot receives `/start TOKEN` command via webhook
5. Backend verifies token and links `chat_id` to user account
6. User receives welcome message

**Reminder Types**:
- **Daily Transaction Reminders**: Sent at user's preferred time (default: 21:00)
- **Weekly Summaries**: Monday 9 AM - Income/expense overview for past week
- **Monthly Reports**: 1st of month, 10 AM - Detailed monthly financial report
- **Subscription Alerts**: 14, 7, 3 days before expiration
- **Inactivity Alerts**: Every 3 days if no transactions in 7+ days

**Scheduler Architecture**:
- APScheduler manages background jobs
- Jobs registered on application startup
- Graceful shutdown on application stop
- Jobs query users with `telegram_chat_id` and `telegram_notifications_enabled=true`
- Failed deliveries (blocked bot) automatically disable notifications

**Message Formatting**:
- HTML formatting for rich text
- Emojis for visual appeal
- Structured data presentation (income/expense breakdown)
- Localized to user timezone (stored in UTC)

**Key Services**:
- `TelegramService`: Bot API interactions, message sending, connection management
- `ReminderScheduler`: Job scheduling, reminder logic, statistics calculation
- Both services initialized on app startup, gracefully shutdown on stop

**Error Handling**:
- Blocked bot → Disable notifications automatically
- Invalid tokens → Clear message to user
- Rate limiting on connection attempts
- Retry logic with exponential backoff

## Key Integration Points

### Webhook Endpoint
- **Path**: `/webhook` (direct endpoint in `main.py`, also duplicated in subscription router)
- **Purpose**: Stripe webhook event handler
- **Events**: `checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.updated`, `customer.subscription.deleted`
- **Signature Verification**: Required via `stripe-signature` header and `STRIPE_WEBHOOK_SECRET`

### Email Templates
Located in `app/templates/` - Jinja2 templates for verification and password reset emails

### Dependency Injection Pattern
Services are injected via `Depends()` in route handlers to access MongoDB connection from `app.mongodb`

## Configuration Requirements

Required environment variables (`.env` file):
- MongoDB: `MONGODB_URL`, `DATABASE_NAME`
- JWT: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`, `STRIPE_WEBHOOK_SECRET`
- Email: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_FROM_NAME`
- App: `FRONTEND_URL`, `CORS_ORIGINS`, `VERIFICATION_TOKEN_EXPIRE_HOURS`
- Telegram (optional): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_URL`

## Common Patterns

### Adding a New Protected Endpoint
```python
@router.get("/new-feature")
@require_subscription(SubscriptionLevel.PRO)
async def new_feature(current_user: UserResponse = Depends(get_current_user)):
    # Implementation
    pass
```

### Checking Feature Access Programmatically
```python
from app.core.subscription import check_feature_access, SubscriptionLevel

check_feature_access(current_user, SubscriptionLevel.PREMIUM, "custom_models")
```

### Service Layer Pattern
All services receive MongoDB database instance in `__init__` and implement business logic separate from route handlers.

## Deployment Notes

Production checklist:
- Replace all Stripe test keys with live keys
- Update Stripe price IDs to production prices
- Configure production webhook URL in Stripe dashboard
- Set production MongoDB instance
- Configure production email service (SMTP)
- Update CORS origins for production domains
- Review and adjust JWT token expiration times
- Set up monitoring for webhook failures and payment errors
- Create Telegram bot via BotFather and configure tokens (if using Telegram features)
- Set up Telegram webhook URL in production (optional, can use polling)
- Monitor Telegram message delivery rates and failed notifications

## Additional Documentation

For detailed guides on specific features:
- **Telegram Integration**: See `TELEGRAM_INTEGRATION_GUIDE.md` for complete setup, API reference, and frontend integration examples
- **Charts & Statistics**: See `CHARTS_AND_STATS_GUIDE.md` for transaction analytics and visualization endpoints
