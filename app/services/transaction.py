from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionStats
from app.services.currency import CurrencyService
import logging

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for managing user income transactions with currency conversion"""

    def __init__(self, db, currency_service: CurrencyService):
        self.db = db
        self.currency_service = currency_service

    async def create_transaction(self, user_id: str, transaction_data: TransactionCreate) -> dict:
        """
        Create a new transaction with currency conversion to GEL.

        Args:
            user_id: User ID
            transaction_data: Transaction data

        Returns:
            Created transaction document
        """
        # Convert to GEL using the transaction date
        transaction_date = transaction_data.transaction_date.date()
        amount_gel, exchange_rate = await self.currency_service.convert_to_gel(
            transaction_data.amount,
            transaction_data.currency,
            transaction_date
        )

        current_time = datetime.now(timezone.utc)

        # Create transaction document
        transaction_dict = {
            "user_id": user_id,
            "amount": transaction_data.amount,
            "currency": transaction_data.currency.upper(),
            "amount_gel": amount_gel,
            "exchange_rate": exchange_rate,
            "conversion_date": current_time,
            "transaction_date": transaction_data.transaction_date,
            "category": transaction_data.category.value,
            "description": transaction_data.description,
            "created_at": current_time,
            "updated_at": current_time
        }

        # Insert into database
        result = await self.db.transactions.insert_one(transaction_dict)
        transaction_dict["id"] = str(result.inserted_id)
        transaction_dict.pop("_id", None)

        logger.info(f"Created transaction {transaction_dict['id']} for user {user_id}")
        return transaction_dict

    async def get_transaction(self, transaction_id: str, user_id: str) -> Optional[dict]:
        """
        Get a transaction by ID.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for access control)

        Returns:
            Transaction document or None
        """
        try:
            transaction = await self.db.transactions.find_one({
                "_id": ObjectId(transaction_id),
                "user_id": user_id
            })

            if transaction:
                transaction["id"] = str(transaction.pop("_id"))
                return transaction

            return None
        except Exception as e:
            logger.error(f"Error getting transaction {transaction_id}: {e}")
            return None

    async def list_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        currency: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> tuple[List[dict], int]:
        """
        List user income transactions with filtering and pagination.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            currency: Filter by currency code
            category: Filter by category
            date_from: Filter by start date
            date_to: Filter by end date

        Returns:
            Tuple of (transactions list, total count)
        """
        # Build query
        query: Dict[str, Any] = {"user_id": user_id}

        if currency:
            query["currency"] = currency.upper()

        if category:
            query["category"] = category

        # Date range filter
        if date_from or date_to:
            date_query: Dict[str, Any] = {}
            if date_from:
                date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
            if date_to:
                date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
            query["transaction_date"] = date_query

        # Get total count
        total = await self.db.transactions.count_documents(query)

        # Get transactions
        cursor = self.db.transactions.find(query).sort("transaction_date", -1).skip(skip).limit(limit)
        transactions = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for transaction in transactions:
            transaction["id"] = str(transaction.pop("_id"))

        return transactions, total

    async def update_transaction(
        self,
        transaction_id: str,
        user_id: str,
        transaction_data: TransactionUpdate
    ) -> Optional[dict]:
        """
        Update a transaction. If amount or currency changes, recalculate GEL conversion.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for access control)
            transaction_data: Updated transaction data

        Returns:
            Updated transaction or None
        """
        # Get existing transaction
        existing = await self.get_transaction(transaction_id, user_id)
        if not existing:
            return None

        # Build update data
        update_data = transaction_data.model_dump(exclude_unset=True)

        # Check if we need to recalculate conversion
        needs_conversion = (
            transaction_data.amount is not None or
            transaction_data.currency is not None or
            transaction_data.transaction_date is not None
        )

        if needs_conversion:
            # Use updated values or fall back to existing
            amount = transaction_data.amount if transaction_data.amount is not None else existing["amount"]
            currency = transaction_data.currency if transaction_data.currency is not None else existing["currency"]
            trans_date = transaction_data.transaction_date if transaction_data.transaction_date is not None else existing["transaction_date"]

            # Convert to date if datetime
            if isinstance(trans_date, datetime):
                trans_date = trans_date.date()

            # Recalculate conversion
            amount_gel, exchange_rate = await self.currency_service.convert_to_gel(
                amount,
                currency,
                trans_date
            )

            update_data["amount_gel"] = amount_gel
            update_data["exchange_rate"] = exchange_rate
            update_data["conversion_date"] = datetime.now(timezone.utc)

        # Uppercase currency if provided
        if "currency" in update_data:
            update_data["currency"] = update_data["currency"].upper()

        # Convert enums to values
        if "type" in update_data and hasattr(update_data["type"], "value"):
            update_data["type"] = update_data["type"].value
        if "category" in update_data and hasattr(update_data["category"], "value"):
            update_data["category"] = update_data["category"].value

        # Update timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)

        # Update in database
        result = await self.db.transactions.update_one(
            {"_id": ObjectId(transaction_id), "user_id": user_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            return None

        # Return updated transaction
        return await self.get_transaction(transaction_id, user_id)

    async def delete_transaction(self, transaction_id: str, user_id: str) -> bool:
        """
        Delete a transaction.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for access control)

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.db.transactions.delete_one({
                "_id": ObjectId(transaction_id),
                "user_id": user_id
            })
            deleted = result.deleted_count > 0
            if deleted:
                logger.info(f"Deleted transaction {transaction_id} for user {user_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting transaction {transaction_id}: {e}")
            return False

    async def get_statistics(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> TransactionStats:
        """
        Get transaction statistics for a user.

        Args:
            user_id: User ID
            date_from: Filter by start date
            date_to: Filter by end date

        Returns:
            Transaction statistics
        """
        # Build query
        query: Dict[str, Any] = {"user_id": user_id}

        if date_from or date_to:
            date_query: Dict[str, Any] = {}
            if date_from:
                date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
            if date_to:
                date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
            query["transaction_date"] = date_query

        # Get all transactions
        cursor = self.db.transactions.find(query)
        transactions = await cursor.to_list(length=None)

        # Calculate statistics - income only
        total_income = 0.0
        currencies = set()
        by_category: Dict[str, float] = {}

        for trans in transactions:
            amount_gel = trans.get("amount_gel", 0.0)
            category = trans.get("category")
            currency = trans.get("currency")

            if currency:
                currencies.add(currency)

            total_income += amount_gel
            if category:
                by_category[category] = by_category.get(category, 0.0) + amount_gel

        return TransactionStats(
            total_income_gel=round(total_income, 2),
            transaction_count=len(transactions),
            currencies_used=sorted(list(currencies)),
            by_category=by_category
        )

    async def get_monthly_statistics(self, user_id: str, year: Optional[int] = None):
        """
        Get monthly statistics for a specific year.

        Args:
            user_id: User ID
            year: Year to get statistics for (default: current year)

        Returns:
            Monthly statistics with totals
        """
        from app.schemas.transaction import MonthlyStats, MonthlyStatsResponse
        from calendar import monthrange

        if year is None:
            year = datetime.now(timezone.utc).year

        # Build aggregation pipeline for MongoDB
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "transaction_date": {
                        "$gte": datetime(year, 1, 1, tzinfo=timezone.utc),
                        "$lt": datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    }
                }
            },
            {
                "$project": {
                    "year": {"$year": "$transaction_date"},
                    "month": {"$month": "$transaction_date"},
                    "amount_gel": 1,
                    "category": 1,
                    "currency": 1
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": "$year",
                        "month": "$month"
                    },
                    "total_income": {"$sum": "$amount_gel"},
                    "count": {"$sum": 1},
                    "categories": {"$push": {"category": "$category", "amount": "$amount_gel"}},
                    "currencies": {"$addToSet": "$currency"}
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1}
            }
        ]

        results = await self.db.transactions.aggregate(pipeline).to_list(length=None)

        months = []
        grand_total = 0.0

        for result in results:
            month_str = f"{result['_id']['year']}-{result['_id']['month']:02d}"
            total_income = result['total_income']
            count = result['count']

            # Calculate category breakdown
            by_category = {}
            for cat_data in result['categories']:
                category = cat_data['category']
                amount = cat_data['amount']
                by_category[category] = by_category.get(category, 0.0) + amount

            months.append(MonthlyStats(
                month=month_str,
                total_income_gel=round(total_income, 2),
                transaction_count=count,
                avg_transaction_gel=round(total_income / count, 2) if count > 0 else 0.0,
                by_category=by_category,
                currencies_used=sorted(result['currencies'])
            ))

            grand_total += total_income

        avg_monthly = grand_total / len(months) if months else 0.0

        return MonthlyStatsResponse(
            months=months,
            total_months=len(months),
            grand_total_gel=round(grand_total, 2),
            avg_monthly_income_gel=round(avg_monthly, 2)
        )

    async def get_current_month_stats(self, user_id: str):
        """
        Get detailed statistics for the current month with projections.

        Args:
            user_id: User ID

        Returns:
            Current month statistics with projections
        """
        from app.schemas.transaction import CurrentMonthStats
        from calendar import monthrange

        now = datetime.now(timezone.utc)
        current_year = now.year
        current_month = now.month

        # Get first and last day of current month
        first_day = datetime(current_year, current_month, 1, tzinfo=timezone.utc)
        days_in_month = monthrange(current_year, current_month)[1]
        last_day = datetime(current_year, current_month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)

        # Get current month transactions
        query = {
            "user_id": user_id,
            "transaction_date": {
                "$gte": first_day,
                "$lte": last_day
            }
        }

        cursor = self.db.transactions.find(query)
        transactions = await cursor.to_list(length=None)

        # Calculate statistics
        total_income = 0.0
        currencies = set()
        by_category = {}

        for trans in transactions:
            amount_gel = trans.get("amount_gel", 0.0)
            category = trans.get("category")
            currency = trans.get("currency")

            if currency:
                currencies.add(currency)

            total_income += amount_gel
            if category:
                by_category[category] = by_category.get(category, 0.0) + amount_gel

        # Calculate days
        days_elapsed = now.day
        days_remaining = days_in_month - days_elapsed

        # Calculate projections
        daily_avg = total_income / days_elapsed if days_elapsed > 0 else 0.0
        projected_income = daily_avg * days_in_month

        # Get last month's total
        if current_month == 1:
            last_month_year = current_year - 1
            last_month = 12
        else:
            last_month_year = current_year
            last_month = current_month - 1

        last_month_first = datetime(last_month_year, last_month, 1, tzinfo=timezone.utc)
        last_month_days = monthrange(last_month_year, last_month)[1]
        last_month_last = datetime(last_month_year, last_month, last_month_days, 23, 59, 59, tzinfo=timezone.utc)

        last_month_query = {
            "user_id": user_id,
            "transaction_date": {
                "$gte": last_month_first,
                "$lte": last_month_last
            }
        }

        last_month_cursor = self.db.transactions.find(last_month_query)
        last_month_trans = await last_month_cursor.to_list(length=None)
        last_month_total = sum(t.get("amount_gel", 0.0) for t in last_month_trans)

        # Calculate month-over-month change
        mom_change = None
        if last_month_total > 0:
            mom_change = round(((total_income - last_month_total) / last_month_total) * 100, 2)

        avg_transaction = total_income / len(transactions) if transactions else 0.0

        return CurrentMonthStats(
            month=f"{current_year}-{current_month:02d}",
            total_income_gel=round(total_income, 2),
            transaction_count=len(transactions),
            avg_transaction_gel=round(avg_transaction, 2),
            by_category=by_category,
            currencies_used=sorted(list(currencies)),
            days_elapsed=days_elapsed,
            days_in_month=days_in_month,
            days_remaining=days_remaining,
            daily_avg_gel=round(daily_avg, 2),
            projected_monthly_income_gel=round(projected_income, 2),
            last_month_income_gel=round(last_month_total, 2) if last_month_total > 0 else None,
            month_over_month_change=mom_change
        )

    async def get_chart_data(
        self,
        user_id: str,
        chart_type: str = "daily",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ):
        """
        Get time-series data for charts.

        Args:
            user_id: User ID
            chart_type: Type of chart (daily, weekly, monthly)
            date_from: Start date
            date_to: End date

        Returns:
            Chart data with time-series points
        """
        from app.schemas.transaction import ChartData, ChartDataPoint
        from datetime import timedelta

        # Set default date range if not provided
        if date_to is None:
            date_to = datetime.now(timezone.utc).date()

        if date_from is None:
            if chart_type == "daily":
                date_from = date_to - timedelta(days=30)
            elif chart_type == "weekly":
                date_from = date_to - timedelta(weeks=12)
            else:  # monthly
                date_from = date_to - timedelta(days=365)

        # Build query
        query = {
            "user_id": user_id,
            "transaction_date": {
                "$gte": datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc),
                "$lte": datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
            }
        }

        # Get all transactions
        cursor = self.db.transactions.find(query).sort("transaction_date", 1)
        transactions = await cursor.to_list(length=None)

        # Group by period
        data_points = {}

        for trans in transactions:
            trans_date = trans.get("transaction_date")
            if isinstance(trans_date, datetime):
                trans_date = trans_date.date()

            if chart_type == "daily":
                key = trans_date.strftime("%Y-%m-%d")
            elif chart_type == "weekly":
                # Get Monday of the week
                week_start = trans_date - timedelta(days=trans_date.weekday())
                key = week_start.strftime("%Y-%m-%d")
            else:  # monthly
                key = trans_date.strftime("%Y-%m")

            amount_gel = trans.get("amount_gel", 0.0)

            if key not in data_points:
                data_points[key] = {"income": 0.0, "count": 0}

            data_points[key]["income"] += amount_gel
            data_points[key]["count"] += 1

        # Convert to list of ChartDataPoint
        chart_points = []
        total_income = 0.0
        total_count = 0

        for date_key in sorted(data_points.keys()):
            income = data_points[date_key]["income"]
            count = data_points[date_key]["count"]

            chart_points.append(ChartDataPoint(
                date=date_key,
                income_gel=round(income, 2),
                transaction_count=count
            ))

            total_income += income
            total_count += count

        return ChartData(
            chart_type=chart_type,
            period_start=date_from.strftime("%Y-%m-%d"),
            period_end=date_to.strftime("%Y-%m-%d"),
            data=chart_points,
            total_income_gel=round(total_income, 2),
            total_transactions=total_count
        )
