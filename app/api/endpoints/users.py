from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_auth_service
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.subscription import require_subscription, SubscriptionLevel
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter(tags=["Users"])

@router.get("/me", 
    response_model=UserResponse,
    description="Get current user information",
    responses={
        200: {"description": "Return current user details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Invalid authentication credentials"}
    })
async def read_user_me(
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Get details of currently authenticated user.
    
    Requires a valid access token in the Authorization header.
    Returns user profile information including:
    - User ID
    - Email
    - Email verification status
    - Subscription plan and status
    """
    # Update last login timestamp
    await auth_service.db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    return current_user

@router.get("/profile/advanced",
    response_model=UserResponse,
    description="Get advanced user profile (Pro+ feature)",
    responses={
        200: {"description": "Advanced user profile"},
        401: {"description": "Not authenticated"},
        403: {"description": "Requires Pro or Premium subscription"}
    })
@require_subscription(SubscriptionLevel.PRO, "Advanced profile features require a Pro subscription or higher")
async def get_advanced_profile(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Get advanced user profile with additional features.
    
    This endpoint demonstrates subscription-based access control.
    Only available to Pro and Premium subscribers.
    """
    # This could include additional user analytics, usage statistics, etc.
    return current_user