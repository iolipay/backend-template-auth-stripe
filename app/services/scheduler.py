"""
Reminder Scheduler Service

Manages scheduled reminders and notifications via Telegram bot.
Uses APScheduler for background job scheduling.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Service for scheduling and sending automated reminders"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.telegram_service = TelegramService(db)
        self.scheduler: Optional[AsyncIOScheduler] = None

    def start(self):
        """Start the scheduler and register all jobs"""
        if not self.telegram_service.is_configured():
            logger.warning("Telegram not configured. Scheduler will not start.")
            return

        self.scheduler = AsyncIOScheduler()

        # Register jobs
        self._register_daily_reminders()
        self._register_weekly_summary()
        self._register_monthly_report()
        self._register_subscription_checks()
        self._register_inactivity_checks()

        # Start scheduler
        self.scheduler.start()
        logger.info("Reminder scheduler started successfully")

    def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Reminder scheduler shut down")

    def _register_daily_reminders(self):
        """Register daily transaction reminder jobs"""
        # We'll send reminders based on each user's preferred time
        # Check every hour for users whose reminder time has passed
        self.scheduler.add_job(
            self.send_daily_reminders,
            trigger=CronTrigger(minute=0),  # Run every hour at the top of the hour
            id="daily_reminders",
            name="Send daily transaction reminders",
            replace_existing=True
        )
        logger.info("Registered daily reminder job")

    def _register_weekly_summary(self):
        """Register weekly summary job (Monday 9 AM)"""
        self.scheduler.add_job(
            self.send_weekly_summaries,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_summaries",
            name="Send weekly summaries",
            replace_existing=True
        )
        logger.info("Registered weekly summary job")

    def _register_monthly_report(self):
        """Register monthly report job (1st of month, 10 AM)"""
        self.scheduler.add_job(
            self.send_monthly_reports,
            trigger=CronTrigger(day=1, hour=10, minute=0),
            id="monthly_reports",
            name="Send monthly reports",
            replace_existing=True
        )
        logger.info("Registered monthly report job")

    def _register_subscription_checks(self):
        """Register subscription expiry check (daily at 10 AM)"""
        self.scheduler.add_job(
            self.check_subscription_expiry,
            trigger=CronTrigger(hour=10, minute=0),
            id="subscription_checks",
            name="Check subscription expiry",
            replace_existing=True
        )
        logger.info("Registered subscription check job")

    def _register_inactivity_checks(self):
        """Register inactivity check (every 3 days at 8 PM)"""
        self.scheduler.add_job(
            self.check_user_inactivity,
            trigger=CronTrigger(hour=20, minute=0, day="*/3"),
            id="inactivity_checks",
            name="Check user inactivity",
            replace_existing=True
        )
        logger.info("Registered inactivity check job")

    async def send_daily_reminders(self):
        """Send daily transaction reminders to all eligible users"""
        try:
            current_hour = datetime.now(timezone.utc).hour

            # Find users who should receive reminders this hour
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            sent_count = 0
            for user in users:
                # Parse user's reminder time (HH:MM format)
                reminder_time = user.get("telegram_reminder_time", "21:00")
                try:
                    reminder_hour = int(reminder_time.split(":")[0])

                    # Check if it's time for this user's reminder
                    if reminder_hour == current_hour:
                        success = await self.telegram_service.send_reminder(
                            chat_id=user["telegram_chat_id"],
                            reminder_type="daily",
                            data={"user_name": user.get("email", "").split("@")[0]}
                        )
                        if success:
                            sent_count += 1

                except (ValueError, IndexError) as e:
                    logger.error(f"Invalid reminder time for user {user['_id']}: {reminder_time}")

            logger.info(f"Sent {sent_count} daily reminders")

        except Exception as e:
            logger.error(f"Error sending daily reminders: {e}")

    async def send_weekly_summaries(self):
        """Send weekly summaries to all eligible users"""
        try:
            # Get all users with Telegram connected
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            # Calculate date range (last 7 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)

            sent_count = 0
            for user in users:
                # Get user's transactions for the week
                transactions = await self.db.transactions.find({
                    "user_id": user["_id"],
                    "transaction_date": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                }).to_list(length=None)

                if not transactions:
                    continue  # Skip users with no transactions

                # Calculate totals
                total_income = sum(
                    t.get("amount_gel", 0) for t in transactions if t.get("type") == "income"
                )
                total_expenses = sum(
                    t.get("amount_gel", 0) for t in transactions if t.get("type") == "expense"
                )

                success = await self.telegram_service.send_reminder(
                    chat_id=user["telegram_chat_id"],
                    reminder_type="weekly",
                    data={
                        "transaction_count": len(transactions),
                        "total_income": total_income,
                        "total_expenses": total_expenses
                    }
                )
                if success:
                    sent_count += 1

            logger.info(f"Sent {sent_count} weekly summaries")

        except Exception as e:
            logger.error(f"Error sending weekly summaries: {e}")

    async def send_monthly_reports(self):
        """Send monthly reports to all eligible users"""
        try:
            # Get all users with Telegram connected
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            # Get last month's date range
            today = datetime.now(timezone.utc)
            first_day_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            month_str = last_month.strftime("%B %Y")

            sent_count = 0
            for user in users:
                # Get user's transactions for last month
                transactions = await self.db.transactions.find({
                    "user_id": user["_id"],
                    "transaction_date": {
                        "$gte": first_day_last_month,
                        "$lt": first_day_this_month
                    }
                }).to_list(length=None)

                if not transactions:
                    continue  # Skip users with no transactions

                # Calculate totals
                total_income = sum(
                    t.get("amount_gel", 0) for t in transactions if t.get("type") == "income"
                )
                total_expenses = sum(
                    t.get("amount_gel", 0) for t in transactions if t.get("type") == "expense"
                )

                # Find top category
                category_totals = {}
                for t in transactions:
                    category = t.get("category", "Other")
                    category_totals[category] = category_totals.get(category, 0) + t.get("amount_gel", 0)

                top_category = None
                top_category_amount = None
                if category_totals:
                    top_category = max(category_totals, key=category_totals.get)
                    top_category_amount = category_totals[top_category]

                success = await self.telegram_service.send_reminder(
                    chat_id=user["telegram_chat_id"],
                    reminder_type="monthly",
                    data={
                        "month": month_str,
                        "transaction_count": len(transactions),
                        "total_income": total_income,
                        "total_expenses": total_expenses,
                        "top_category": top_category,
                        "top_category_amount": top_category_amount
                    }
                )
                if success:
                    sent_count += 1

            logger.info(f"Sent {sent_count} monthly reports")

        except Exception as e:
            logger.error(f"Error sending monthly reports: {e}")

    async def check_subscription_expiry(self):
        """Check for expiring subscriptions and send alerts"""
        try:
            # Find users with subscriptions expiring in 3, 7, or 14 days
            alert_days = [3, 7, 14]
            today = datetime.now(timezone.utc)

            sent_count = 0
            for days in alert_days:
                target_date = today + timedelta(days=days)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)

                # Find users whose subscription expires on target date
                users = await self.db.users.find({
                    "telegram_chat_id": {"$ne": None},
                    "telegram_notifications_enabled": True,
                    "subscription_plan": {"$in": ["pro", "premium"]},
                    "subscription_end_date": {
                        "$gte": start_of_day,
                        "$lt": end_of_day
                    }
                }).to_list(length=None)

                for user in users:
                    success = await self.telegram_service.send_reminder(
                        chat_id=user["telegram_chat_id"],
                        reminder_type="subscription",
                        data={
                            "plan": user.get("subscription_plan", ""),
                            "days_remaining": days
                        }
                    )
                    if success:
                        sent_count += 1

            logger.info(f"Sent {sent_count} subscription expiry alerts")

        except Exception as e:
            logger.error(f"Error checking subscription expiry: {e}")

    async def check_user_inactivity(self):
        """Check for inactive users and send re-engagement messages"""
        try:
            # Find users who haven't logged transactions in 7+ days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            sent_count = 0
            for user in users:
                # Check last transaction date
                last_transaction = await self.db.transactions.find_one(
                    {"user_id": user["_id"]},
                    sort=[("transaction_date", -1)]
                )

                if not last_transaction:
                    continue  # Skip users with no transactions ever

                last_date = last_transaction.get("transaction_date")
                if last_date and last_date < cutoff_date:
                    days_inactive = (datetime.now(timezone.utc) - last_date).days

                    success = await self.telegram_service.send_reminder(
                        chat_id=user["telegram_chat_id"],
                        reminder_type="inactivity",
                        data={"days_inactive": days_inactive}
                    )
                    if success:
                        sent_count += 1

            logger.info(f"Sent {sent_count} inactivity alerts")

        except Exception as e:
            logger.error(f"Error checking user inactivity: {e}")

    async def send_test_reminder(self, user_id: str, reminder_type: str = "daily") -> bool:
        """
        Send a test reminder to a specific user

        Args:
            user_id: User ID
            reminder_type: Type of reminder to send

        Returns:
            True if successful
        """
        # Convert user_id to ObjectId if it's a string
        user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        user = await self.db.users.find_one({"_id": user_object_id})

        if not user or not user.get("telegram_chat_id"):
            logger.error(f"User {user_id} does not have Telegram connected")
            return False

        # Prepare test data based on reminder type
        test_data = {}
        if reminder_type == "daily":
            test_data = {"user_name": user.get("email", "").split("@")[0]}
        elif reminder_type == "weekly":
            test_data = {
                "transaction_count": 10,
                "total_income": 5000.00,
                "total_expenses": 2000.00
            }
        elif reminder_type == "monthly":
            test_data = {
                "month": datetime.now().strftime("%B %Y"),
                "transaction_count": 25,
                "total_income": 15000.00,
                "total_expenses": 8000.00,
                "top_category": "Salary",
                "top_category_amount": 12000.00
            }
        elif reminder_type == "subscription":
            test_data = {
                "plan": user.get("subscription_plan", "pro"),
                "days_remaining": 3
            }
        elif reminder_type == "inactivity":
            test_data = {"days_inactive": 7}

        return await self.telegram_service.send_reminder(
            chat_id=user["telegram_chat_id"],
            reminder_type=reminder_type,
            data=test_data
        )
