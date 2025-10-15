from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class TransactionCategory(str, Enum):
    # Income categories only
    SALARY = "salary"
    FREELANCE = "freelance"
    BUSINESS = "business"
    INVESTMENT = "investment"
    RENTAL_INCOME = "rental_income"
    DIVIDENDS = "dividends"
    BONUS = "bonus"
    COMMISSION = "commission"
    OTHER = "other"


class Transaction(BaseModel):
    id: str
    user_id: str

    # Original transaction data
    amount: float = Field(..., description="Original amount in original currency")
    currency: str = Field(..., description="Original currency code (e.g., USD, EUR)")

    # Converted to GEL
    amount_gel: float = Field(..., description="Amount converted to GEL")
    exchange_rate: float = Field(..., description="Exchange rate used for conversion")
    conversion_date: datetime = Field(..., description="Date when the conversion was performed")

    # Transaction metadata
    transaction_date: datetime = Field(..., description="Date of the income")
    category: TransactionCategory = Field(..., description="Income category")
    description: Optional[str] = Field(None, description="Optional description")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransactionInDB(BaseModel):
    user_id: str
    amount: float
    currency: str
    amount_gel: float
    exchange_rate: float
    conversion_date: datetime
    transaction_date: datetime
    category: TransactionCategory
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
