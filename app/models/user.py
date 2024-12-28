from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

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
    created_at: datetime = datetime.utcnow()
    verification_token: Optional[str] = None
    verification_sent_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    subscription_status: Optional[str] = None
    subscription_end_date: Optional[datetime] = None

class User(UserBase):
    id: str
    created_at: datetime
    subscription_status: Optional[str] = None 