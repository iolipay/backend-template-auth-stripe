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


class MonthlyStats(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    total_income_gel: float = Field(..., description="Total income for the month in GEL")
    transaction_count: int = Field(..., description="Number of transactions in the month")
    avg_transaction_gel: float = Field(..., description="Average transaction amount in GEL")
    by_category: dict = Field(..., description="Breakdown by category in GEL")
    currencies_used: List[str] = Field(..., description="Currencies used in this month")

    class Config:
        json_schema_extra = {
            "example": {
                "month": "2025-10",
                "total_income_gel": 15000.00,
                "transaction_count": 25,
                "avg_transaction_gel": 600.00,
                "by_category": {
                    "salary": 12000.00,
                    "freelance": 3000.00
                },
                "currencies_used": ["USD", "EUR", "GEL"]
            }
        }


class MonthlyStatsResponse(BaseModel):
    months: List[MonthlyStats] = Field(..., description="List of monthly statistics")
    total_months: int = Field(..., description="Number of months included")
    grand_total_gel: float = Field(..., description="Total income across all months in GEL")
    avg_monthly_income_gel: float = Field(..., description="Average monthly income in GEL")

    class Config:
        json_schema_extra = {
            "example": {
                "months": [
                    {
                        "month": "2025-10",
                        "total_income_gel": 15000.00,
                        "transaction_count": 25,
                        "avg_transaction_gel": 600.00,
                        "by_category": {"salary": 12000.00, "freelance": 3000.00},
                        "currencies_used": ["USD", "EUR"]
                    }
                ],
                "total_months": 12,
                "grand_total_gel": 180000.00,
                "avg_monthly_income_gel": 15000.00
            }
        }


class CurrentMonthStats(BaseModel):
    month: str = Field(..., description="Current month in YYYY-MM format")
    total_income_gel: float = Field(..., description="Income so far this month in GEL")
    transaction_count: int = Field(..., description="Number of transactions this month")
    avg_transaction_gel: float = Field(..., description="Average transaction amount in GEL")
    by_category: dict = Field(..., description="Breakdown by category in GEL")
    currencies_used: List[str] = Field(..., description="Currencies used this month")
    days_elapsed: int = Field(..., description="Days elapsed in current month")
    days_in_month: int = Field(..., description="Total days in current month")
    days_remaining: int = Field(..., description="Days remaining in current month")
    daily_avg_gel: float = Field(..., description="Daily average income in GEL")
    projected_monthly_income_gel: float = Field(..., description="Projected total for the month in GEL")
    last_month_income_gel: Optional[float] = Field(None, description="Last month's total income in GEL")
    month_over_month_change: Optional[float] = Field(None, description="Percentage change vs last month")

    class Config:
        json_schema_extra = {
            "example": {
                "month": "2025-10",
                "total_income_gel": 8500.00,
                "transaction_count": 12,
                "avg_transaction_gel": 708.33,
                "by_category": {"salary": 6000.00, "freelance": 2500.00},
                "currencies_used": ["USD", "EUR"],
                "days_elapsed": 15,
                "days_in_month": 31,
                "days_remaining": 16,
                "daily_avg_gel": 566.67,
                "projected_monthly_income_gel": 17566.77,
                "last_month_income_gel": 15000.00,
                "month_over_month_change": 17.11
            }
        }


class ChartDataPoint(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    income_gel: float = Field(..., description="Total income for this period in GEL")
    transaction_count: int = Field(..., description="Number of transactions in this period")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-15",
                "income_gel": 1200.50,
                "transaction_count": 3
            }
        }


class ChartData(BaseModel):
    chart_type: str = Field(..., description="Type of chart data: daily, weekly, or monthly")
    period_start: str = Field(..., description="Start date of the period (YYYY-MM-DD)")
    period_end: str = Field(..., description="End date of the period (YYYY-MM-DD)")
    data: List[ChartDataPoint] = Field(..., description="Data points for the chart")
    total_income_gel: float = Field(..., description="Total income for the entire period in GEL")
    total_transactions: int = Field(..., description="Total transactions for the entire period")

    class Config:
        json_schema_extra = {
            "example": {
                "chart_type": "daily",
                "period_start": "2025-09-15",
                "period_end": "2025-10-15",
                "data": [
                    {"date": "2025-10-01", "income_gel": 500.00, "transaction_count": 2},
                    {"date": "2025-10-02", "income_gel": 300.00, "transaction_count": 1}
                ],
                "total_income_gel": 15000.00,
                "total_transactions": 45
            }
        }
