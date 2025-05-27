from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
import re
from typing import Any, Dict
from bson import ObjectId
from jose import JWTError, jwt
from app.core.security import create_access_token, get_password_hash, verify_password, validate_password
from app.core.exceptions import InvalidCredentialsError, InvalidEmailError, UserExistsError, InvalidTokenError, UserNotFoundError, IncorrectPasswordError, WeakPasswordError
from app.services.email import EmailService
from app.core.config import settings
import asyncio

class AuthService:
    def __init__(self, db):
        self.db = db
        self.email_service = EmailService()

    async def create_user_with_verification(self, user_create):
        # Check if user exists
        if await self.db.users.find_one({"email": user_create.email}):
            raise UserExistsError()

        # Validate password strength
        if not validate_password(user_create.password):
            raise WeakPasswordError()

        # Create verification token
        verification_token = create_access_token(
            data={"email": user_create.email},
            expires_delta=timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
        )

        # Create user
        user_dict = user_create.model_dump()
        current_time = datetime.now(timezone.utc)
        user_dict.update({
            "hashed_password": get_password_hash(user_dict.pop("password")),
            "verification_token": verification_token,
            "verification_sent_at": current_time,
            "created_at": current_time,
            "is_verified": False
        })

        result = await self.db.users.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)

        # Send verification email in background
        asyncio.create_task(
            self.email_service.send_verification_email(
                user_create.email,
                verification_token
            )
        )

        return user_dict
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        if not self._validate_email(email):
            raise InvalidEmailError()

        user = await self.db.users.find_one({"email": email})
        if not user:
            raise InvalidCredentialsError()

        if not verify_password(password, user["hashed_password"]):
            raise InvalidCredentialsError()

        return user


    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise UserNotFoundError()
            
            user["id"] = str(user["_id"])
            return user
        except Exception:
            raise UserNotFoundError()

    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))


    async def verify_email(self, token: str):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email = payload.get("email")
            if not email:
                raise InvalidTokenError()
        except JWTError:
            raise InvalidTokenError()

        user = await self.db.users.find_one({"email": email})
        if not user or user["verification_token"] != token:
            raise InvalidTokenError()

        # Update user verification status
        await self.db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "is_verified": True,
                    "verified_at": datetime.now(timezone.utc),
                    "verification_token": None
                }
            }
        )

        # Send success email
        await self.email_service.send_verification_success(email)

        return True

    async def get_last_verification_sent(self, email: str) -> datetime:
        user = await self.db.users.find_one({"email": email})
        if not user:
            raise UserNotFoundError()
        return user.get("last_verification_sent")

    async def resend_verification(self, email: str):
        user = await self.db.users.find_one({"email": email})
        if not user:
            raise UserNotFoundError()
        
        if user.get("is_verified"):
            raise HTTPException(
                status_code=400,
                detail="Email is already verified"
            )

        # Create new verification token
        verification_token = create_access_token(
            data={"email": email},
            expires_delta=timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
        )

        # Update user with new token
        await self.db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "verification_token": verification_token,
                    "verification_sent_at": datetime.now(timezone.utc)
                }
            }
        )

        # Send verification email asynchronously
        asyncio.create_task(
            self.email_service.send_verification_email(email, verification_token)
        )

        # Update last verification sent time
        await self.db.users.update_one(
            {"email": email},
            {"$set": {"last_verification_sent": datetime.now(timezone.utc)}}
        )

        return {"message": "Verification email sent"}

    async def send_password_reset(self, email: str):
        """Send password reset email to user"""
        user = await self.db.users.find_one({"email": email})
        if not user:
            raise UserNotFoundError()

        # Create reset token
        reset_token = create_access_token(
            data={"email": email, "type": "password_reset"},
            expires_delta=timedelta(hours=1)  # Token expires in 1 hour
        )

        # Store reset token in database
        await self.db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires": datetime.now(timezone.utc) + timedelta(hours=1)
                }
            }
        )

        # Send reset email asynchronously
        asyncio.create_task(
            self.email_service.send_password_reset_email(email, reset_token)
        )

    async def reset_password(self, token: str, new_password: str):
        """Reset user password using reset token"""
        # Validate new password strength
        if not validate_password(new_password):
            raise WeakPasswordError()
            
        try:
            # Verify token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email = payload.get("email")
            token_type = payload.get("type")
            
            if not email or token_type != "password_reset":
                raise InvalidTokenError()

            # Get user and verify token
            user = await self.db.users.find_one({
                "email": email,
                "reset_token": token,
                "reset_token_expires": {"$gt": datetime.now(timezone.utc)}
            })

            if not user:
                raise InvalidTokenError()

            # Update password
            hashed_password = get_password_hash(new_password)
            await self.db.users.update_one(
                {"email": email},
                {
                    "$set": {
                        "hashed_password": hashed_password,
                        "reset_token": None,
                        "reset_token_expires": None
                    }
                }
            )

            # Send password changed confirmation email
            asyncio.create_task(
                self.email_service.send_password_changed_email(email)
            )

        except JWTError:
            raise InvalidTokenError()

    async def update_password(self, user_id: str, current_password: str, new_password: str) -> None:
        """
        Update user's password after verifying current password.
        
        Args:
            user_id: The ID of the user
            current_password: The current password to verify
            new_password: The new password to set
            
        Raises:
            IncorrectPasswordError: If the current password is incorrect
            UserNotFoundError: If the user is not found
            ValueError: If the new password is same as current password
        """
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise UserNotFoundError("User not found")
            
        if not verify_password(current_password, user["hashed_password"]):
            raise IncorrectPasswordError("Current password is incorrect")
        
        # Validate new password strength
        if not validate_password(new_password):
            raise WeakPasswordError()
        
        # Check if new password is same as current password
        if verify_password(new_password, user["hashed_password"]):
            raise ValueError("New password must be different from current password")
            
        hashed_password = get_password_hash(new_password)
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"hashed_password": hashed_password}}
        )