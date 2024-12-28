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


class PasswordChange(BaseModel):
    current_password: str
    new_password: str