from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verification_token: Optional[str] = None
    verification_sent_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    subscription_plan: str = "free"  # "free", "pro", "premium"
    subscription_status: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    last_login: Optional[datetime] = None

    # Telegram integration fields
    telegram_chat_id: Optional[int] = None
    telegram_username: Optional[str] = None
    telegram_connected_at: Optional[datetime] = None
    telegram_notifications_enabled: bool = True
    telegram_reminder_time: str = "21:00"  # Default daily reminder time (HH:MM format)
    telegram_connection_token: Optional[str] = None
    telegram_connection_token_expires: Optional[datetime] = None

class User(UserBase):
    id: str
    created_at: datetime
    subscription_plan: str = "free"
    subscription_status: Optional[str] = None 