# backend template

A FastAPI application with MongoDB integration, authentication, and future Stripe subscription support.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp .env.example .env
```

Then edit `.env` with your configuration:

```
MONGODB_URL=your_mongodb_url
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
```

3. Run the application:

```bash
uvicorn app.main:app --reload
```

## Features

- FastAPI REST API
- MongoDB integration using Motor
- JWT Authentication
- User registration and login
- Password hashing with bcrypt
- Async database operations
- Future Stripe subscription integration

## API Endpoints

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh access token

### Users

- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile

## Development

### Running Tests
