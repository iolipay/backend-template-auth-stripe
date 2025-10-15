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
        self._register_tax_reminders()
        self._register_monthly_tax_summary()
        self._register_threshold_checks()

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

    # ========== Tax Reminder Jobs ==========

    def _register_tax_reminders(self):
        """Register tax declaration reminder check (daily at 9 AM)"""
        self.scheduler.add_job(
            self.check_tax_declaration_deadlines,
            trigger=CronTrigger(hour=9, minute=0),
            id="tax_declaration_reminders",
            name="Check tax declaration deadlines",
            replace_existing=True
        )
        logger.info("Registered tax declaration reminder job")

    def _register_monthly_tax_summary(self):
        """Register monthly tax summary (1st of month, 9 AM)"""
        self.scheduler.add_job(
            self.send_monthly_tax_summaries,
            trigger=CronTrigger(day=1, hour=9, minute=0),
            id="monthly_tax_summaries",
            name="Send monthly tax summaries",
            replace_existing=True
        )
        logger.info("Registered monthly tax summary job")

    def _register_threshold_checks(self):
        """Register threshold warning checks (weekly, Monday 10 AM)"""
        self.scheduler.add_job(
            self.check_threshold_warnings,
            trigger=CronTrigger(day_of_week="mon", hour=10, minute=0),
            id="threshold_checks",
            name="Check threshold warnings",
            replace_existing=True
        )
        logger.info("Registered threshold warning check job")

    async def check_tax_declaration_deadlines(self):
        """Check for upcoming tax declaration deadlines and send reminders"""
        try:
            from app.services.tax_stats import TaxStatsService

            # Get all users with Telegram connected
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            current_date = datetime.now(timezone.utc)
            sent_count = 0

            for user in users:
                user_id = str(user["_id"])
                tax_service = TaxStatsService(self.db)

                # Get pending declarations
                pending_declarations = await self.db.tax_declarations.find({
                    "user_id": user_id,
                    "status": {"$in": ["pending", "overdue"]},
                    "filing_deadline": {"$gte": current_date}
                }).sort("filing_deadline", 1).to_list(length=None)

                for decl in pending_declarations:
                    days_until = (decl["filing_deadline"] - current_date).days

                    # Send reminders at 7, 3, and 1 day before deadline
                    if days_until in [7, 3, 1]:
                        month_name = datetime(decl["year"], decl["month"], 1).strftime("%B %Y")

                        success = await self.telegram_service.send_reminder(
                            chat_id=user["telegram_chat_id"],
                            reminder_type="tax_declaration",
                            data={
                                "month_name": month_name,
                                "income_gel": decl.get("income_gel", 0),
                                "tax_gel": decl.get("tax_due_gel", 0),
                                "days_until": days_until
                            }
                        )
                        if success:
                            sent_count += 1

            logger.info(f"Sent {sent_count} tax declaration reminders")

        except Exception as e:
            logger.error(f"Error checking tax declaration deadlines: {e}")

    async def send_monthly_tax_summaries(self):
        """Send monthly tax summaries on 1st of each month"""
        try:
            from app.services.tax_stats import TaxStatsService

            # Get all users with Telegram connected
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            current_date = datetime.now(timezone.utc)
            # Get last month's data
            if current_date.month == 1:
                last_month_year = current_date.year - 1
                last_month = 12
            else:
                last_month_year = current_date.year
                last_month = current_date.month - 1

            month_name = datetime(last_month_year, last_month, 1).strftime("%B %Y")
            sent_count = 0

            for user in users:
                user_id = str(user["_id"])
                tax_service = TaxStatsService(self.db)

                # Get or create declaration for last month
                declaration = await self.db.tax_declarations.find_one({
                    "user_id": user_id,
                    "year": last_month_year,
                    "month": last_month
                })

                if not declaration or declaration.get("income_gel", 0) <= 0:
                    continue  # Skip users with no income last month

                # Get YTD overview
                overview = await tax_service.get_tax_overview(user_id, last_month_year)

                deadline = declaration["filing_deadline"].strftime("%B %d")

                success = await self.telegram_service.send_reminder(
                    chat_id=user["telegram_chat_id"],
                    reminder_type="monthly_tax_summary",
                    data={
                        "month_name": month_name,
                        "income_gel": declaration.get("income_gel", 0),
                        "tax_gel": declaration.get("tax_due_gel", 0),
                        "transaction_count": declaration.get("transaction_count", 0),
                        "deadline": deadline,
                        "ytd_income": overview.total_income_ytd_gel,
                        "ytd_tax": overview.tax_liability_ytd_gel,
                        "threshold_percentage": overview.threshold_percentage_used
                    }
                )
                if success:
                    sent_count += 1

            logger.info(f"Sent {sent_count} monthly tax summaries")

        except Exception as e:
            logger.error(f"Error sending monthly tax summaries: {e}")

    async def check_threshold_warnings(self):
        """Check for users approaching or exceeding threshold and send warnings"""
        try:
            from app.services.tax_stats import TaxStatsService

            # Get all users with Telegram connected
            users = await self.db.users.find({
                "telegram_chat_id": {"$ne": None},
                "telegram_notifications_enabled": True,
            }).to_list(length=None)

            current_year = datetime.now(timezone.utc).year
            sent_count = 0

            for user in users:
                user_id = str(user["_id"])
                tax_service = TaxStatsService(self.db)

                # Get tax overview
                overview = await tax_service.get_tax_overview(user_id, current_year)

                # Send warnings at specific thresholds
                threshold_pct = overview.threshold_percentage_used

                should_send = False
                severity = "info"

                if threshold_pct >= 95:
                    should_send = True
                    severity = "critical"
                elif threshold_pct >= 85:
                    should_send = True
                    severity = "high"
                elif threshold_pct >= 75:
                    should_send = True
                    severity = "medium"

                if should_send:
                    success = await self.telegram_service.send_reminder(
                        chat_id=user["telegram_chat_id"],
                        reminder_type="threshold_warning",
                        data={
                            "threshold_percentage": threshold_pct,
                            "remaining_gel": overview.threshold_remaining_gel,
                            "severity": severity
                        }
                    )
                    if success:
                        sent_count += 1

            logger.info(f"Sent {sent_count} threshold warnings")

        except Exception as e:
            logger.error(f"Error checking threshold warnings: {e}")
