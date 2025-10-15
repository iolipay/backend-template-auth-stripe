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
