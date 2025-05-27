from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserResponse
import logging

logger = logging.getLogger(__name__)

class SubscriptionLevel:
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

# Define subscription hierarchy (higher levels include lower level features)
SUBSCRIPTION_HIERARCHY = {
    SubscriptionLevel.FREE: 0,
    SubscriptionLevel.PRO: 1, 
    SubscriptionLevel.PREMIUM: 2
}

def require_subscription(
    required_level: str,
    message: Optional[str] = None
):
    """
    Decorator to require a minimum subscription level for an endpoint.
    
    Args:
        required_level: Minimum subscription level required ("free", "pro", "premium")
        message: Custom error message if access is denied
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserResponse):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check subscription level
            user_level = current_user.subscription_plan or SubscriptionLevel.FREE
            
            if not has_access(user_level, required_level):
                error_message = message or f"This feature requires a {required_level} subscription or higher"
                raise HTTPException(
                    status_code=403,
                    detail=error_message
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_access(user_level: str, required_level: str) -> bool:
    """
    Check if user subscription level meets the required level.
    
    Args:
        user_level: User's current subscription level
        required_level: Required subscription level
        
    Returns:
        True if user has access, False otherwise
    """
    user_rank = SUBSCRIPTION_HIERARCHY.get(user_level, 0)
    required_rank = SUBSCRIPTION_HIERARCHY.get(required_level, 0)
    return user_rank >= required_rank

def check_feature_access(
    user: UserResponse,
    required_level: str,
    feature_name: str = "feature"
) -> None:
    """
    Check if user has access to a specific feature based on subscription level.
    Raises HTTPException if access is denied.
    
    Args:
        user: Current user
        required_level: Required subscription level
        feature_name: Name of the feature for error message
    """
    if not has_access(user.subscription_plan or SubscriptionLevel.FREE, required_level):
        raise HTTPException(
            status_code=403,
            detail=f"Access to {feature_name} requires a {required_level} subscription or higher. "
                   f"Your current plan: {user.subscription_plan or 'free'}"
        )

# Usage limits by subscription level
USAGE_LIMITS = {
    SubscriptionLevel.FREE: {
        "api_calls_per_day": 100,
        "chat_messages_per_day": 50,
        "file_uploads_per_month": 5,
        "max_file_size_mb": 10
    },
    SubscriptionLevel.PRO: {
        "api_calls_per_day": 1000,
        "chat_messages_per_day": 500,
        "file_uploads_per_month": 50,
        "max_file_size_mb": 100
    },
    SubscriptionLevel.PREMIUM: {
        "api_calls_per_day": 10000,
        "chat_messages_per_day": 5000,
        "file_uploads_per_month": 500,
        "max_file_size_mb": 1000
    }
}

def get_usage_limits(subscription_level: str) -> dict:
    """
    Get usage limits for a subscription level.
    
    Args:
        subscription_level: User's subscription level
        
    Returns:
        Dictionary containing usage limits
    """
    return USAGE_LIMITS.get(subscription_level, USAGE_LIMITS[SubscriptionLevel.FREE])

def check_usage_limit(
    user: UserResponse,
    limit_type: str,
    current_usage: int,
    increment: int = 1
) -> None:
    """
    Check if user would exceed usage limits with the given increment.
    
    Args:
        user: Current user
        limit_type: Type of limit to check (e.g., "api_calls_per_day")
        current_usage: Current usage count
        increment: Amount to increment (default: 1)
    """
    limits = get_usage_limits(user.subscription_plan or SubscriptionLevel.FREE)
    limit = limits.get(limit_type)
    
    if limit is not None and (current_usage + increment) > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Usage limit exceeded. Your {user.subscription_plan or 'free'} plan allows "
                   f"{limit} {limit_type.replace('_', ' ')}. "
                   f"Upgrade your subscription for higher limits."
        )

# Feature availability by subscription level
FEATURE_ACCESS = {
    "basic_chat": [SubscriptionLevel.FREE, SubscriptionLevel.PRO, SubscriptionLevel.PREMIUM],
    "advanced_chat": [SubscriptionLevel.PRO, SubscriptionLevel.PREMIUM],
    "file_upload": [SubscriptionLevel.PRO, SubscriptionLevel.PREMIUM],
    "priority_support": [SubscriptionLevel.PRO, SubscriptionLevel.PREMIUM],
    "custom_models": [SubscriptionLevel.PREMIUM],
    "api_access": [SubscriptionLevel.PREMIUM],
    "team_collaboration": [SubscriptionLevel.PREMIUM]
}

def has_feature_access(user_level: str, feature: str) -> bool:
    """
    Check if user has access to a specific feature.
    
    Args:
        user_level: User's subscription level
        feature: Feature name
        
    Returns:
        True if user has access to the feature
    """
    allowed_levels = FEATURE_ACCESS.get(feature, [])
    return user_level in allowed_levels

def require_feature(feature: str):
    """
    Decorator to require access to a specific feature.
    
    Args:
        feature: Feature name to check access for
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserResponse):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            user_level = current_user.subscription_plan or SubscriptionLevel.FREE
            
            if not has_feature_access(user_level, feature):
                allowed_levels = FEATURE_ACCESS.get(feature, [])
                min_required = min(allowed_levels, key=lambda x: SUBSCRIPTION_HIERARCHY[x]) if allowed_levels else "premium"
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Access to {feature.replace('_', ' ')} requires a {min_required} subscription or higher. "
                           f"Your current plan: {user_level}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 