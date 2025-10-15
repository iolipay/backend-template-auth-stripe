"""
Telegram Bot Service

Handles all Telegram Bot API interactions including:
- Sending messages and reminders
- Managing user connections
- Formatting notification messages
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
import logging
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for interacting with Telegram Bot API"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.bot: Optional[Bot] = None

        # Initialize bot if token is configured
        if settings.TELEGRAM_BOT_TOKEN:
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not configured. Telegram features will be disabled.")

    def is_configured(self) -> bool:
        """Check if Telegram bot is properly configured"""
        return self.bot is not None and settings.TELEGRAM_BOT_TOKEN is not None

    async def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information"""
        if not self.is_configured():
            raise ValueError("Telegram bot is not configured")

        try:
            bot_user = await self.bot.get_me()
            return {
                "id": bot_user.id,
                "username": bot_user.username,
                "first_name": bot_user.first_name,
                "can_join_groups": bot_user.can_join_groups,
                "can_read_all_group_messages": bot_user.can_read_all_group_messages
            }
        except TelegramError as e:
            logger.error(f"Error getting bot info: {e}")
            raise

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a text message to a user

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Message formatting (HTML or Markdown)
            disable_notification: Send silently without notification

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Cannot send message: Telegram bot not configured")
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )
            logger.info(f"Message sent to chat_id {chat_id}")
            return True

        except Forbidden:
            # User blocked the bot
            logger.warning(f"User {chat_id} has blocked the bot")
            await self._handle_blocked_user(chat_id)
            return False

        except BadRequest as e:
            logger.error(f"Bad request sending message to {chat_id}: {e}")
            return False

        except TelegramError as e:
            logger.error(f"Telegram error sending message to {chat_id}: {e}")
            return False

    async def _handle_blocked_user(self, chat_id: int):
        """Handle case where user has blocked the bot"""
        # Disable notifications for this user
        await self.db.users.update_one(
            {"telegram_chat_id": chat_id},
            {"$set": {"telegram_notifications_enabled": False}}
        )
        logger.info(f"Disabled notifications for blocked user {chat_id}")

    async def generate_connection_token(self, user_id: str) -> Dict[str, Any]:
        """
        Generate a connection token for linking Telegram account

        Args:
            user_id: User ID from database

        Returns:
            Dictionary with token, deep link, and expiration info
        """
        if not self.is_configured():
            raise ValueError("Telegram bot is not configured")

        # Generate secure random token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Store token in user document
        # Convert user_id to ObjectId if it's a string
        user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        await self.db.users.update_one(
            {"_id": user_object_id},
            {
                "$set": {
                    "telegram_connection_token": token,
                    "telegram_connection_token_expires": expires_at
                }
            }
        )

        # Create deep link
        bot_username = settings.TELEGRAM_BOT_USERNAME or (await self.get_bot_info())["username"]
        deep_link = f"https://t.me/{bot_username}?start={token}"

        return {
            "connection_token": token,
            "deep_link": deep_link,
            "bot_username": bot_username,
            "expires_at": expires_at
        }

    async def verify_connection_token(
        self,
        token: str,
        chat_id: int,
        telegram_username: Optional[str] = None
    ) -> Optional[str]:
        """
        Verify connection token and link Telegram account to user

        Args:
            token: Connection token from /start command
            chat_id: Telegram chat ID
            telegram_username: Telegram username (optional)

        Returns:
            User ID if successful, None otherwise
        """
        # Find user with this token
        user = await self.db.users.find_one({
            "telegram_connection_token": token,
            "telegram_connection_token_expires": {"$gt": datetime.now(timezone.utc)}
        })

        if not user:
            logger.warning(f"Invalid or expired token: {token}")
            return None

        # Link Telegram account to user
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "telegram_chat_id": chat_id,
                    "telegram_username": telegram_username,
                    "telegram_connected_at": datetime.now(timezone.utc),
                    "telegram_notifications_enabled": True
                },
                "$unset": {
                    "telegram_connection_token": "",
                    "telegram_connection_token_expires": ""
                }
            }
        )

        logger.info(f"Successfully linked Telegram account {telegram_username or chat_id} to user {user['_id']}")
        return str(user["_id"])

    async def disconnect_telegram(self, user_id: str) -> bool:
        """
        Disconnect Telegram account from user

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        # Convert user_id to ObjectId if it's a string
        user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        result = await self.db.users.update_one(
            {"_id": user_object_id},
            {
                "$unset": {
                    "telegram_chat_id": "",
                    "telegram_username": "",
                    "telegram_connected_at": ""
                },
                "$set": {
                    "telegram_notifications_enabled": False
                }
            }
        )

        return result.modified_count > 0

    # Message formatting methods

    def format_daily_reminder(self, user_name: Optional[str] = None) -> str:
        """Format daily transaction reminder message"""
        greeting = f"Hi {user_name}! 👋\n\n" if user_name else "Hi! 👋\n\n"
        return (
            f"{greeting}"
            f"💰 <b>Daily Reminder</b>\n\n"
            f"Don't forget to log today's transactions!\n\n"
            f"Keep your financial tracking up to date. 📊"
        )

    def format_weekly_summary(
        self,
        transaction_count: int,
        total_income: float,
        total_expenses: float
    ) -> str:
        """Format weekly summary message"""
        balance = total_income - total_expenses
        balance_emoji = "📈" if balance > 0 else "📉" if balance < 0 else "➡️"

        return (
            f"📊 <b>Weekly Summary</b>\n\n"
            f"📥 Income: {total_income:.2f} GEL\n"
            f"📤 Expenses: {total_expenses:.2f} GEL\n"
            f"{balance_emoji} Balance: {balance:.2f} GEL\n\n"
            f"Total transactions: {transaction_count}\n\n"
            f"Keep up the good work! 💪"
        )

    def format_monthly_report(
        self,
        month: str,
        total_income: float,
        total_expenses: float,
        transaction_count: int,
        top_category: Optional[str] = None,
        top_category_amount: Optional[float] = None
    ) -> str:
        """Format monthly report message"""
        balance = total_income - total_expenses
        balance_emoji = "📈" if balance > 0 else "📉" if balance < 0 else "➡️"

        message = (
            f"📈 <b>Monthly Report - {month}</b>\n\n"
            f"📥 Total Income: {total_income:.2f} GEL\n"
            f"📤 Total Expenses: {total_expenses:.2f} GEL\n"
            f"{balance_emoji} Net Balance: {balance:.2f} GEL\n\n"
            f"📊 Transactions: {transaction_count}\n"
        )

        if top_category and top_category_amount:
            message += f"\n🏆 Top category: {top_category} ({top_category_amount:.2f} GEL)"

        return message

    def format_subscription_reminder(
        self,
        plan: str,
        days_remaining: int
    ) -> str:
        """Format subscription expiry reminder"""
        emoji = "⚠️" if days_remaining <= 3 else "ℹ️"

        return (
            f"{emoji} <b>Subscription Reminder</b>\n\n"
            f"Your <b>{plan.title()}</b> subscription expires in <b>{days_remaining} day(s)</b>.\n\n"
            f"Renew now to continue enjoying premium features! 🚀"
        )

    def format_inactivity_alert(self, days_inactive: int) -> str:
        """Format inactivity alert message"""
        return (
            f"👋 <b>We miss you!</b>\n\n"
            f"You haven't logged any transactions in <b>{days_inactive} days</b>.\n\n"
            f"Stay on top of your finances - log your recent transactions now! 💰"
        )

    def format_goal_achievement(self, goal_type: str, amount: float) -> str:
        """Format goal achievement message"""
        return (
            f"🎉 <b>Congratulations!</b>\n\n"
            f"You've reached your {goal_type} goal of {amount:.2f} GEL! 🏆\n\n"
            f"Keep up the excellent work! 💪"
        )

    def format_welcome_message(self) -> str:
        """Format welcome message after successful connection"""
        return (
            f"✅ <b>Successfully Connected!</b>\n\n"
            f"Your Telegram account is now linked to your platform account.\n\n"
            f"You'll receive:\n"
            f"• Daily transaction reminders 💰\n"
            f"• Weekly summaries 📊\n"
            f"• Monthly reports 📈\n"
            f"• Subscription alerts ⚠️\n\n"
            f"You can manage your notification preferences in the app settings."
        )

    async def send_reminder(
        self,
        chat_id: int,
        reminder_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a formatted reminder message

        Args:
            chat_id: Telegram chat ID
            reminder_type: Type of reminder (daily, weekly, monthly, etc.)
            data: Additional data for formatting the message

        Returns:
            True if message sent successfully
        """
        data = data or {}

        # Format message based on type
        if reminder_type == "daily":
            text = self.format_daily_reminder(data.get("user_name"))
        elif reminder_type == "weekly":
            text = self.format_weekly_summary(
                data.get("transaction_count", 0),
                data.get("total_income", 0),
                data.get("total_expenses", 0)
            )
        elif reminder_type == "monthly":
            text = self.format_monthly_report(
                data.get("month", ""),
                data.get("total_income", 0),
                data.get("total_expenses", 0),
                data.get("transaction_count", 0),
                data.get("top_category"),
                data.get("top_category_amount")
            )
        elif reminder_type == "subscription":
            text = self.format_subscription_reminder(
                data.get("plan", ""),
                data.get("days_remaining", 0)
            )
        elif reminder_type == "inactivity":
            text = self.format_inactivity_alert(data.get("days_inactive", 0))
        elif reminder_type == "goal":
            text = self.format_goal_achievement(
                data.get("goal_type", ""),
                data.get("amount", 0)
            )
        elif reminder_type == "welcome":
            text = self.format_welcome_message()
        else:
            logger.error(f"Unknown reminder type: {reminder_type}")
            return False

        return await self.send_message(chat_id, text)
