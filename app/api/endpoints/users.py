from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["Users"])

@router.get("/me", 
    response_model=UserResponse,
    description="Get current user information",
    responses={
        200: {"description": "Return current user details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Invalid authentication credentials"}
    })
async def read_user_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Get details of currently authenticated user.
    
    Requires a valid access token in the Authorization header.
    Returns user profile information including:
    - User ID
    - Email
    - First name
    - Last name
    - Email verification status
    """
    return current_user