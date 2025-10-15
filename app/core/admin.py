"""Admin role system for tax declaration filing service"""

from functools import wraps
from fastapi import HTTPException, status
from app.schemas.user import UserResponse


def require_admin(func):
    """Decorator to require admin privileges for an endpoint"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find current_user in kwargs
        current_user = kwargs.get('current_user')
        if not current_user:
            # Try to find it in args (if passed positionally)
            for arg in args:
                if isinstance(arg, UserResponse):
                    current_user = arg
                    break

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )

        return await func(*args, **kwargs)

    return wrapper


def is_admin_user(user: UserResponse) -> bool:
    """Check if user has admin privileges"""
    return user.is_admin
