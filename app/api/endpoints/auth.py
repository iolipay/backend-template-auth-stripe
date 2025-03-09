from app.core.exceptions import IncorrectPasswordError, InvalidTokenError, UserNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.core.security import create_access_token
from app.api.deps import get_auth_service, get_current_user
from app.schemas.user import PasswordChange
from datetime import datetime, timedelta

router = APIRouter(tags=["Authentication"])

@router.post("/register", response_model=UserResponse, 
    description="Register a new user account",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or email already registered"}
    })
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Register a new user with the following information:
    - email: Valid email address
    - password: Minimum 8 characters
    - first_name: User's first name
    - last_name: User's last name

    Returns the created user information and sends a verification email.
    """
    return await auth_service.create_user_with_verification(user_data)

@router.post("/login",
    description="Authenticate user and return access token",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Incorrect email or password"}
    })
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with user credentials:
    - username: User's email address
    - password: User's password

    Returns an access token for authenticated requests.
    """
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password",
    description="Change user password (requires authentication)",
    responses={
        200: {"description": "Password updated successfully"},
        401: {"description": "Current password is incorrect"},
        403: {"description": "Not authenticated"},
        400: {"description": "Invalid new password"}
    })
async def change_password(
    password_data: PasswordChange,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change the current user's password. Requires:
    - current_password: User's current password
    - new_password: New password (minimum 8 characters)
    
    The new password must be different from the current password.
    Must be authenticated with a valid access token.
    """
    try:
        await auth_service.update_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password
        )
        return {"detail": "Password updated successfully"}
    except IncorrectPasswordError:
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.get("/verify/{token}",
    description="Verify user's email address",
    responses={
        200: {"description": "Email verified successfully"},
        400: {"description": "Invalid or expired verification token"}
    })
async def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify user's email address using the token sent to their email.
    Token is typically valid for 24 hours after registration or resending verification.
    """
    try:
        await auth_service.verify_email(token)
        return {"detail": "Email verified successfully"}
    except InvalidTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )

@router.post("/resend-verification",
    description="Resend email verification link",
    responses={
        200: {"description": "Verification email resent"},
        404: {"description": "User not found"},
        429: {"description": "Too many requests - wait before trying again"}
    })
async def resend_verification(
    email: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Resend verification email to user's email address.
    Rate limited to one request every 2 minutes.
    """
    try:
        last_sent = await auth_service.get_last_verification_sent(email)
        if last_sent:
            time_diff = datetime.utcnow() - last_sent
            if time_diff < timedelta(minutes=2):
                raise HTTPException(
                    status_code=429,
                    detail="Please wait 2 minutes before requesting another verification email"
                )
        
        await auth_service.resend_verification(email)
        return {"detail": "Verification email resent"}
    except UserNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    except HTTPException as e:
        raise e

@router.post("/forgot-password",
    description="Request password reset email",
    responses={
        200: {"description": "Password reset email sent"}
    })
async def forgot_password(
    email: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request a password reset email for the provided email address.
    If the email exists in our system, a reset link will be sent.
    For security reasons, the API returns success even if the email is not found.
    """
    try:
        await auth_service.send_password_reset(email)
        return {"detail": "Password reset email sent"}
    except UserNotFoundError:
        return {"detail": "Password reset email sent"}

@router.post("/reset-password/{token}",
    description="Reset password using reset token",
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired reset token"}
    })
async def reset_password(
    token: str,
    new_password: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset user's password using the token sent to their email.
    Requires:
    - token: Valid password reset token
    - new_password: New password (minimum 8 characters)
    
    Token is typically valid for 1 hour after requesting password reset.
    """
    try:
        await auth_service.reset_password(token, new_password)
        return {"detail": "Password reset successfully"}
    except InvalidTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )