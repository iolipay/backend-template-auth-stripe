from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from app.api.deps import get_current_user, get_transaction_service
from app.schemas.user import UserResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TransactionStats,
    CurrencyRate
)
from app.services.transaction import TransactionService
from app.services.currency import get_currency_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transactions"])


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=201,
    description="Create a new income transaction with automatic GEL conversion"
)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """
    Create a new income transaction.

    The amount will be automatically converted to GEL using the official
    National Bank of Georgia exchange rate for the transaction date.
    """
    try:
        transaction = await transaction_service.create_transaction(
            current_user.id,
            transaction_data
        )
        return TransactionResponse(**transaction)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to create transaction")


@router.get(
    "/",
    response_model=TransactionListResponse,
    description="List user income transactions with filtering and pagination"
)
async def list_transactions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g., USD, EUR)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionListResponse:
    """
    Get a list of user income transactions with optional filtering.

    Supports filtering by:
    - Currency
    - Category
    - Date range

    Results are sorted by transaction date (newest first).
    """
    try:
        transactions, total = await transaction_service.list_transactions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            currency=currency,
            category=category,
            date_from=date_from,
            date_to=date_to
        )

        return TransactionListResponse(
            transactions=[TransactionResponse(**t) for t in transactions],
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list transactions")


@router.get(
    "/stats",
    response_model=TransactionStats,
    description="Get income statistics and summary"
)
async def get_statistics(
    date_from: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionStats:
    """
    Get income statistics including:
    - Total income in GEL
    - Transaction count
    - Breakdown by category
    - Currencies used

    Optionally filter by date range.
    """
    try:
        stats = await transaction_service.get_statistics(
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    description="Get a specific transaction by ID"
)
async def get_transaction(
    transaction_id: str,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """Get details of a specific transaction."""
    transaction = await transaction_service.get_transaction(transaction_id, current_user.id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(**transaction)


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    description="Update a transaction"
)
async def update_transaction(
    transaction_id: str,
    transaction_data: TransactionUpdate,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """
    Update a transaction.

    If amount, currency, or transaction date is changed, the GEL conversion
    will be automatically recalculated using the new values.
    """
    try:
        transaction = await transaction_service.update_transaction(
            transaction_id,
            current_user.id,
            transaction_data
        )

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionResponse(**transaction)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to update transaction")


@router.delete(
    "/{transaction_id}",
    status_code=204,
    description="Delete a transaction"
)
async def delete_transaction(
    transaction_id: str,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """Delete a transaction permanently."""
    deleted = await transaction_service.delete_transaction(transaction_id, current_user.id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return None


@router.get(
    "/currencies/available",
    response_model=List[str],
    description="Get list of available currencies"
)
async def get_available_currencies(
    target_date: Optional[date] = Query(None, description="Date for exchange rates (default: today)")
):
    """
    Get list of currencies available for transaction creation.

    Includes GEL and all currencies available from the National Bank of Georgia.
    """
    try:
        currency_service = get_currency_service()
        currencies = await currency_service.get_available_currencies(target_date)
        return currencies
    except Exception as e:
        logger.error(f"Error getting available currencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available currencies")


@router.get(
    "/currencies/rate",
    response_model=CurrencyRate,
    description="Get exchange rate for a specific currency"
)
async def get_currency_rate(
    currency: str = Query(..., description="Currency code (e.g., USD, EUR)"),
    target_date: Optional[date] = Query(None, description="Date for exchange rate (default: today)")
):
    """
    Get the current exchange rate for a currency to GEL.

    Uses official rates from the National Bank of Georgia.
    """
    try:
        currency_service = get_currency_service()
        rate = await currency_service.get_exchange_rate(currency, target_date)

        return CurrencyRate(
            currency=currency.upper(),
            rate=rate,
            date=target_date or date.today()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exchange rate: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exchange rate")
