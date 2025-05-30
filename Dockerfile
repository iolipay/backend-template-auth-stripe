FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV MONGODB_URL=mongo_uri
ENV DATABASE_NAME=db_name

ENV SECRET_KEY=your-secret-key-here
ENV ALGORITHM=HS256
ENV ACCESS_TOKEN_EXPIRE_MINUTES=30

ENV STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
ENV STRIPE_PUBLIC_KEY=pk_test_your-stripe-public-key
ENV STRIPE_WEBHOOK_SECRET=whsec_your-stripe-webhook-secret

# Email Settings for PrivateEmail
ENV MAIL_SERVER=mail.privateemail.com
ENV MAIL_PORT=587
ENV MAIL_USERNAME=your-email@example.com
ENV MAIL_PASSWORD=your-email-password
ENV MAIL_FROM=your-email@example.com
ENV MAIL_FROM_NAME=Seeky

ENV VERIFICATION_TOKEN_EXPIRE_HOURS=24

# Frontend URL should match your actual frontend
ENV FRONTEND_URL=http://localhost:3000

ENV CORS_ORIGINS=http://localhost:3000,http://localhost:8000

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]