from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.models.transaction import TransactionCategory


class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Income amount (must be positive)")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code (e.g., USD, EUR, GEL)")
    transaction_date: datetime = Field(..., description="Date of the income")
    category: TransactionCategory = Field(..., description="Income category")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1500.50,
                "currency": "USD",
                "transaction_date": "2025-10-15T10:30:00Z",
                "category": "salary",
                "description": "Monthly salary payment"
            }
        }


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0, description="Income amount (must be positive)")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency code")
    transaction_date: Optional[datetime] = Field(None, description="Date of the income")
    category: Optional[TransactionCategory] = Field(None, description="Income category")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str
    amount_gel: float
    exchange_rate: float
    conversion_date: datetime
    transaction_date: datetime
    category: TransactionCategory
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "amount": 1500.50,
                "currency": "USD",
                "amount_gel": 4066.36,
                "exchange_rate": 2.7111,
                "conversion_date": "2025-10-15T10:30:00Z",
                "transaction_date": "2025-10-15T10:30:00Z",
                "category": "salary",
                "description": "Monthly salary payment",
                "created_at": "2025-10-15T10:30:00Z",
                "updated_at": "2025-10-15T10:30:00Z"
            }
        }


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    skip: int
    limit: int


class TransactionStats(BaseModel):
    total_income_gel: float = Field(..., description="Total income in GEL")
    transaction_count: int = Field(..., description="Total number of income transactions")
    currencies_used: List[str] = Field(..., description="List of currencies used")
    by_category: dict = Field(..., description="Breakdown by category in GEL")

    class Config:
        json_schema_extra = {
            "example": {
                "total_income_gel": 15000.00,
                "transaction_count": 25,
                "currencies_used": ["USD", "EUR", "GEL"],
                "by_category": {
                    "salary": 12000.00,
                    "freelance": 3000.00,
                    "business": 5000.00
                }
            }
        }


class CurrencyRate(BaseModel):
    currency: str
    rate: float
    date: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "currency": "USD",
                "rate": 2.7111,
                "date": "2025-10-15T00:00:00Z"
            }
        }
