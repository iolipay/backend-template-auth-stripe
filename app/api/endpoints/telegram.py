"""
Telegram Integration API Endpoints

Handles:
- Connecting/disconnecting Telegram accounts
- Managing notification preferences
- Processing webhook updates from Telegram
- Testing reminders
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from typing import Dict, Any, Optional
from bson import ObjectId
from app.api.deps import get_current_user, get_telegram_service, get_scheduler_service
from app.schemas.user import (
    UserResponse,
    TelegramConnectionResponse,
    TelegramSettings,
    TelegramSettingsUpdate,
    TelegramStatusResponse
)
from app.services.telegram import TelegramService
from app.services.scheduler import ReminderScheduler
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telegram Integration"])


@router.post("/connect", response_model=TelegramConnectionResponse)
async def connect_telegram(
    current_user: UserResponse = Depends(get_current_user),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Generate a connection token and deep link for linking Telegram account

    Returns a deep link that the user should click to start the bot
    and complete the connection process.
    """
    if not telegram_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Telegram integration is not configured on the server"
        )

    # Check if user already has Telegram connected
    if current_user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram account is already connected. Disconnect first to link a different account."
        )

    try:
        connection_data = await telegram_service.generate_connection_token(current_user.id)
        return TelegramConnectionResponse(**connection_data)

    except Exception as e:
        logger.error(f"Error generating connection token: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate connection token")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint for receiving updates from Telegram

    This endpoint processes incoming messages and commands from Telegram users.
    Main use case: handling /start command with connection token.

    Note: In production, configure this URL in Telegram webhook settings.
    For development, you can use polling mode or tools like ngrok.
    """
    try:
        # Get the update data
        update_data = await request.json()
        logger.info(f"Received Telegram update: {update_data}")

        # Extract message data
        message = update_data.get("message")
        if not message:
            return {"ok": True}  # Not a message update, ignore

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        username = message.get("chat", {}).get("username")

        # Handle /start command with token
        if text.startswith("/start "):
            token = text.split(" ", 1)[1].strip()

            # Get services
            from app.main import app
            telegram_service = TelegramService(app.mongodb)

            # Verify and link account
            user_id = await telegram_service.verify_connection_token(
                token=token,
                chat_id=chat_id,
                telegram_username=username
            )

            if user_id:
                # Send welcome message
                await telegram_service.send_reminder(
                    chat_id=chat_id,
                    reminder_type="welcome"
                )
                logger.info(f"Successfully linked Telegram account for user {user_id}")
            else:
                # Send error message
                await telegram_service.send_message(
                    chat_id=chat_id,
                    text="❌ Invalid or expired connection link. Please generate a new one from the app."
                )

        elif text == "/start":
            # Regular start command without token
            from app.main import app
            telegram_service = TelegramService(app.mongodb)
            await telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    "👋 Welcome to the Transaction Tracker Bot!\n\n"
                    "To connect your account, please visit the app and click 'Connect Telegram' "
                    "in your settings."
                )
            )

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"ok": False, "error": str(e)}


@router.delete("/disconnect")
async def disconnect_telegram(
    current_user: UserResponse = Depends(get_current_user),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Disconnect Telegram account from user profile

    This will remove the Telegram link and disable all notifications.
    """
    if not current_user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="No Telegram account is connected"
        )

    try:
        success = await telegram_service.disconnect_telegram(current_user.id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to disconnect Telegram account")

        return {"message": "Telegram account disconnected successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Telegram: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Telegram account")


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current Telegram connection status

    Returns information about whether Telegram is connected
    and notification settings.
    """
    return TelegramStatusResponse(
        is_connected=current_user.telegram_chat_id is not None,
        telegram_username=current_user.telegram_username,
        connected_at=current_user.telegram_connected_at,
        notifications_enabled=current_user.telegram_notifications_enabled
    )


@router.get("/settings", response_model=TelegramSettings)
async def get_telegram_settings(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get Telegram notification preferences

    Returns all notification settings for the user.
    """
    if not current_user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="No Telegram account is connected"
        )

    # For now, return default settings
    # In a future update, these could be stored per-user in the database
    return TelegramSettings(
        notifications_enabled=current_user.telegram_notifications_enabled,
        reminder_time=current_user.telegram_reminder_time,
        daily_transaction_reminder=True,
        weekly_summary=True,
        monthly_report=True,
        subscription_alerts=True
    )


@router.put("/settings", response_model=TelegramSettings)
async def update_telegram_settings(
    settings: TelegramSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Update Telegram notification preferences

    Allows users to customize their notification settings,
    including enabling/disabling notifications and setting reminder time.
    """
    if not current_user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="No Telegram account is connected"
        )

    try:
        from app.main import app

        # Prepare update data
        update_data = {}

        if settings.notifications_enabled is not None:
            update_data["telegram_notifications_enabled"] = settings.notifications_enabled

        if settings.reminder_time is not None:
            # Validate time format (HH:MM)
            try:
                hours, minutes = settings.reminder_time.split(":")
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    raise ValueError("Invalid time range")
                update_data["telegram_reminder_time"] = settings.reminder_time
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid time format. Use HH:MM format (e.g., 21:00)"
                )

        # Convert user_id to ObjectId
        user_object_id = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id

        # Update user settings
        if update_data:
            await app.mongodb.users.update_one(
                {"_id": user_object_id},
                {"$set": update_data}
            )

        # Get updated user data
        updated_user = await app.mongodb.users.find_one({"_id": user_object_id})

        return TelegramSettings(
            notifications_enabled=updated_user.get("telegram_notifications_enabled", True),
            reminder_time=updated_user.get("telegram_reminder_time", "21:00"),
            daily_transaction_reminder=settings.daily_transaction_reminder or True,
            weekly_summary=settings.weekly_summary or True,
            monthly_report=settings.monthly_report or True,
            subscription_alerts=settings.subscription_alerts or True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Telegram settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.post("/test-reminder")
async def send_test_reminder(
    reminder_type: str = Body(..., embed=True),
    current_user: UserResponse = Depends(get_current_user),
    scheduler_service: ReminderScheduler = Depends(get_scheduler_service)
):
    """
    Send a test reminder to verify Telegram integration

    Available reminder types:
    - daily: Daily transaction reminder
    - weekly: Weekly summary
    - monthly: Monthly report
    - subscription: Subscription expiry alert
    - inactivity: Inactivity alert
    """
    if not current_user.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="No Telegram account is connected"
        )

    valid_types = ["daily", "weekly", "monthly", "subscription", "inactivity"]
    if reminder_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reminder type. Must be one of: {', '.join(valid_types)}"
        )

    try:
        success = await scheduler_service.send_test_reminder(
            user_id=current_user.id,
            reminder_type=reminder_type
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to send test reminder. Check if bot is accessible."
            )

        return {
            "message": f"Test {reminder_type} reminder sent successfully",
            "reminder_type": reminder_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test reminder: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test reminder")


@router.get("/bot-info")
async def get_bot_info(
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Get information about the Telegram bot

    Returns bot username and other details.
    Useful for debugging and displaying bot info in the frontend.
    """
    if not telegram_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Telegram integration is not configured on the server"
        )

    try:
        bot_info = await telegram_service.get_bot_info()
        return bot_info

    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bot information")
