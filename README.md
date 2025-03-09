# FastAPI MongoDB Authentication API Overview

Your backend API is a comprehensive authentication system built with FastAPI and MongoDB, providing essential user authentication and account management functionality. Here's what it does:

## Core Functionality

- **User Registration**: Creates new user accounts storing email and securely hashed passwords
- **User Authentication**: Validates credentials and issues access tokens (OAuth2/JWT based)
- **Account Management**: Allows users to view their profile information

## Security Features

- **Email Verification**: Implements a verification workflow with tokenized email links
- **Password Management**:
  - Password change (for authenticated users)
  - Password reset via email (forgot password flow)
  - Secure token-based password reset mechanism

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

### .env

```
# MongoDB settings
MONGODB_URL=your_mongodb_url
DATABASE_NAME=your_database_name

# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Future Stripe Settings
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Email Settings
MAIL_SERVER=your-mail-server
MAIL_PORT=465
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=your-email@example.com
MAIL_FROM_NAME=YourAppName

# Verification Settings
VERIFICATION_TOKEN_EXPIRE_HOURS=24
```

The system includes proper validation, error handling, and rate limiting (for verification emails), following security best practices for user authentication workflows.
