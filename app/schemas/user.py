from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime

class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_verified: bool = False
    subscription_plan: str = "free"
    subscription_status: Optional[str] = None

    # Telegram fields
    telegram_chat_id: Optional[int] = None
    telegram_username: Optional[str] = None
    telegram_connected_at: Optional[datetime] = None
    telegram_notifications_enabled: bool = True
    telegram_reminder_time: str = "21:00"


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Telegram-specific schemas
class TelegramConnectionResponse(BaseModel):
    connection_token: str
    deep_link: str
    bot_username: str
    expires_at: datetime
    instructions: str = "Click the link above to connect your Telegram account"


class TelegramSettings(BaseModel):
    notifications_enabled: bool = True
    reminder_time: str = "21:00"  # HH:MM format
    daily_transaction_reminder: bool = True
    weekly_summary: bool = True
    monthly_report: bool = True
    subscription_alerts: bool = True


class TelegramSettingsUpdate(BaseModel):
    notifications_enabled: Optional[bool] = None
    reminder_time: Optional[str] = None
    daily_transaction_reminder: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    monthly_report: Optional[bool] = None
    subscription_alerts: Optional[bool] = None


class TelegramStatusResponse(BaseModel):
    is_connected: bool
    telegram_username: Optional[str] = None
    connected_at: Optional[datetime] = None
    notifications_enabled: bool = False