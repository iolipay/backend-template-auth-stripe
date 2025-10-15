from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from app.models.tax_declaration import DeclarationStatus


class ThresholdStatus(str, Enum):
    """Status relative to annual income threshold"""
    ON_TRACK = "on_track"  # Under 75%
    APPROACHING_LIMIT = "approaching_limit"  # 75-90%
    NEAR_LIMIT = "near_limit"  # 90-100%
    EXCEEDED = "exceeded"  # Over 100%


class InsightType(str, Enum):
    """Type of tax insight"""
    DECLARATION_REMINDER = "declaration_reminder"
    THRESHOLD_WARNING = "threshold_warning"
    INCOME_SPIKE = "income_spike"
    INCOME_DROP = "income_drop"
    OPTIMIZATION_TIP = "optimization_tip"
    COMPLIANCE_ALERT = "compliance_alert"


class InsightSeverity(str, Enum):
    """Severity level of insight"""
    INFO = "info"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ========== Tax Overview ==========

class TaxOverview(BaseModel):
    """
    Overview of current year tax status
    Main dashboard summary
    """
    year: int = Field(..., description="Tax year")
    total_income_ytd_gel: float = Field(..., description="Year-to-date income in GEL")
    tax_liability_ytd_gel: float = Field(..., description="Year-to-date tax liability (1%)")
    threshold_remaining_gel: float = Field(..., description="Remaining before 500k threshold")
    threshold_percentage_used: float = Field(..., description="Percentage of threshold used (0-100+)")
    status: ThresholdStatus = Field(..., description="Current threshold status")
    months_declared: int = Field(..., description="Number of declarations submitted")
    months_pending: int = Field(..., description="Number of pending declarations")
    last_declaration_date: Optional[datetime] = Field(None, description="Last declaration submission date")
    next_declaration_due: Optional[datetime] = Field(None, description="Next declaration deadline")

    class Config:
        json_schema_extra = {
            "example": {
                "year": 2025,
                "total_income_ytd_gel": 245000.00,
                "tax_liability_ytd_gel": 2450.00,
                "threshold_remaining_gel": 255000.00,
                "threshold_percentage_used": 49.0,
                "status": "on_track",
                "months_declared": 9,
                "months_pending": 1,
                "last_declaration_date": "2025-10-05T10:30:00Z",
                "next_declaration_due": "2025-11-15T23:59:59Z"
            }
        }


# ========== Monthly Tax Summary ==========

class MonthlyTaxSummary(BaseModel):
    """Tax summary for a specific month"""
    month: str = Field(..., description="Month in YYYY-MM format")
    income_gel: float = Field(..., description="Total income for the month")
    tax_due_gel: float = Field(..., description="Tax due (1% of income)")
    declaration_status: str = Field(..., description="Status: pending, submitted, or overdue")
    filing_deadline: datetime = Field(..., description="Deadline for filing")
    submitted_date: Optional[datetime] = Field(None, description="Actual submission date")
    days_until_deadline: Optional[int] = Field(None, description="Days until deadline (if pending)")
    transaction_count: int = Field(default=0, description="Number of transactions")

    class Config:
        json_schema_extra = {
            "example": {
                "month": "2025-10",
                "income_gel": 22000.00,
                "tax_due_gel": 220.00,
                "declaration_status": "pending",
                "filing_deadline": "2025-11-15T23:59:59Z",
                "submitted_date": None,
                "days_until_deadline": 5,
                "transaction_count": 15
            }
        }


class MonthlyTaxBreakdown(BaseModel):
    """Complete monthly tax breakdown for a year"""
    year: int = Field(..., description="Tax year")
    months: List[MonthlyTaxSummary] = Field(..., description="Monthly summaries")
    total_income_gel: float = Field(..., description="Total income for the year")
    total_tax_gel: float = Field(..., description="Total tax for the year")
    avg_monthly_income_gel: float = Field(..., description="Average monthly income")
    avg_monthly_tax_gel: float = Field(..., description="Average monthly tax")

    class Config:
        json_schema_extra = {
            "example": {
                "year": 2025,
                "months": [
                    {
                        "month": "2025-01",
                        "income_gel": 18500.00,
                        "tax_due_gel": 185.00,
                        "declaration_status": "submitted",
                        "filing_deadline": "2025-02-15T23:59:59Z",
                        "submitted_date": "2025-02-05T10:00:00Z",
                        "days_until_deadline": None,
                        "transaction_count": 12
                    }
                ],
                "total_income_gel": 245000.00,
                "total_tax_gel": 2450.00,
                "avg_monthly_income_gel": 24500.00,
                "avg_monthly_tax_gel": 245.00
            }
        }


# ========== Tax Projections ==========

class ThresholdRisk(BaseModel):
    """Risk assessment for exceeding threshold"""
    will_exceed_threshold: bool = Field(..., description="Whether threshold will be exceeded at current pace")
    threshold_gel: float = Field(default=500000.00, description="Annual threshold limit")
    projected_remaining_gel: float = Field(..., description="Projected remaining amount")
    risk_level: str = Field(..., description="Risk level: low, medium, high")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")


class TaxProjection(BaseModel):
    """Forward-looking tax projections"""
    based_on_months: int = Field(..., description="Number of months used for projection")
    current_income_gel: float = Field(..., description="Income so far this year")
    current_tax_gel: float = Field(..., description="Tax liability so far")
    projected_annual_income_gel: float = Field(..., description="Projected total annual income")
    projected_annual_tax_gel: float = Field(..., description="Projected total annual tax")
    threshold_status: ThresholdRisk = Field(..., description="Threshold risk assessment")
    monthly_avg_needed_for_threshold: float = Field(..., description="Avg monthly income to reach threshold")
    recommendation: str = Field(..., description="Human-readable recommendation")

    class Config:
        json_schema_extra = {
            "example": {
                "based_on_months": 10,
                "current_income_gel": 245000.00,
                "current_tax_gel": 2450.00,
                "projected_annual_income_gel": 294000.00,
                "projected_annual_tax_gel": 2940.00,
                "threshold_status": {
                    "will_exceed_threshold": False,
                    "threshold_gel": 500000.00,
                    "projected_remaining_gel": 206000.00,
                    "risk_level": "low",
                    "confidence": 0.85
                },
                "monthly_avg_needed_for_threshold": 41666.67,
                "recommendation": "You're on track. Current pace keeps you under the 500k limit."
            }
        }


# ========== Tax Insights ==========

class TaxInsight(BaseModel):
    """Smart insight or alert"""
    type: InsightType = Field(..., description="Type of insight")
    severity: InsightSeverity = Field(..., description="Severity level")
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Detailed message")
    action_url: Optional[str] = Field(None, description="URL for action")
    action_text: Optional[str] = Field(None, description="Action button text")
    action_required: bool = Field(default=False, description="Whether action is required")
    created_at: datetime = Field(..., description="When insight was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "declaration_reminder",
                "severity": "high",
                "title": "October Declaration Due Soon",
                "message": "Your October declaration is due in 5 days (Nov 15). Income: 22,000 GEL, Tax: 220 GEL",
                "action_url": "/declarations/2025-10",
                "action_text": "Prepare Declaration",
                "action_required": True,
                "created_at": "2025-11-10T09:00:00Z"
            }
        }


class TaxInsightsList(BaseModel):
    """Collection of tax insights"""
    insights: List[TaxInsight] = Field(..., description="List of insights")
    total_insights: int = Field(..., description="Total number of insights")
    high_priority_count: int = Field(..., description="Number of high/critical priority insights")

    class Config:
        json_schema_extra = {
            "example": {
                "insights": [
                    {
                        "type": "declaration_reminder",
                        "severity": "high",
                        "title": "October Declaration Due Soon",
                        "message": "Your October declaration is due in 5 days.",
                        "action_url": "/declarations/2025-10",
                        "action_text": "Prepare Declaration",
                        "action_required": True,
                        "created_at": "2025-11-10T09:00:00Z"
                    }
                ],
                "total_insights": 3,
                "high_priority_count": 1
            }
        }


# ========== Tax Comparison ==========

class YearlyTaxSummary(BaseModel):
    """Tax summary for a single year"""
    year: int = Field(..., description="Year")
    total_income_gel: float = Field(..., description="Total income for the year")
    total_tax_gel: float = Field(..., description="Total tax paid")
    avg_monthly_income_gel: float = Field(..., description="Average monthly income")
    months_with_income: int = Field(..., description="Number of months with income")
    growth_vs_previous: Optional[float] = Field(None, description="Growth percentage vs previous year")


class TaxComparison(BaseModel):
    """Year-over-year tax comparison"""
    years: List[YearlyTaxSummary] = Field(..., description="Yearly summaries")
    total_tax_paid_all_years: float = Field(..., description="Total tax paid across all years")

    class Config:
        json_schema_extra = {
            "example": {
                "years": [
                    {
                        "year": 2025,
                        "total_income_gel": 245000.00,
                        "total_tax_gel": 2450.00,
                        "avg_monthly_income_gel": 24500.00,
                        "months_with_income": 10,
                        "growth_vs_previous": 15.5
                    },
                    {
                        "year": 2024,
                        "total_income_gel": 212000.00,
                        "total_tax_gel": 2120.00,
                        "avg_monthly_income_gel": 17666.67,
                        "months_with_income": 12,
                        "growth_vs_previous": None
                    }
                ],
                "total_tax_paid_all_years": 4570.00
            }
        }


# ========== Declaration Management ==========

class FilingServicePaymentInfo(BaseModel):
    """Preview of admin filing service payment breakdown"""
    available: bool = Field(..., description="Whether filing service is available for this declaration")
    tax_amount: float = Field(..., description="Tax amount (1% to government)")
    service_fee: float = Field(..., description="Service fee (configurable % to company)")
    total_payment: float = Field(..., description="Total payment amount")
    breakdown: str = Field(..., description="Human-readable fee breakdown")

    class Config:
        json_schema_extra = {
            "example": {
                "available": True,
                "tax_amount": 220.00,
                "service_fee": 440.00,
                "total_payment": 660.00,
                "breakdown": "3% of income (1% tax + 2% service fee)"
            }
        }


class DeclarationDetails(BaseModel):
    """Detailed information for a specific declaration"""
    year: int
    month: int
    month_name: str = Field(..., description="Month name (e.g., 'October 2025')")
    income_gel: float
    tax_due_gel: float
    transaction_count: int
    declaration_status: str
    filing_deadline: datetime
    submitted_date: Optional[datetime] = None
    days_until_deadline: Optional[int] = None
    is_overdue: bool = Field(default=False)
    filing_service: Optional[FilingServicePaymentInfo] = Field(None, description="Admin filing service payment preview")

    class Config:
        json_schema_extra = {
            "example": {
                "year": 2025,
                "month": 10,
                "month_name": "October 2025",
                "income_gel": 22000.00,
                "tax_due_gel": 220.00,
                "transaction_count": 15,
                "declaration_status": "pending",
                "filing_deadline": "2025-11-15T23:59:59Z",
                "submitted_date": None,
                "days_until_deadline": 5,
                "is_overdue": False,
                "filing_service": {
                    "available": True,
                    "tax_amount": 220.00,
                    "service_fee": 440.00,
                    "total_payment": 660.00,
                    "breakdown": "3% of income (1% tax + 2% service fee)"
                }
            }
        }


class MarkDeclarationRequest(BaseModel):
    """Request to mark declaration as submitted"""
    submitted_date: Optional[datetime] = Field(None, description="Submission date (defaults to now)")


class MarkDeclarationResponse(BaseModel):
    """Response after marking declaration"""
    success: bool
    message: str
    declaration: DeclarationDetails


# ========== Tax Charts ==========

class TaxChartDataPoint(BaseModel):
    """Single data point for tax charts"""
    date: str = Field(..., description="Date label")
    income: float = Field(..., description="Income amount")
    tax: float = Field(..., description="Tax amount")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-01",
                "income": 18500.00,
                "tax": 185.00
            }
        }


class TaxChartData(BaseModel):
    """Chart data for visualizations"""
    chart_type: str = Field(..., description="Type of chart: monthly_tax, cumulative_tax, threshold_progress")
    data: List[TaxChartDataPoint] = Field(..., description="Data points")
    total_income: float = Field(..., description="Total income across all points")
    total_tax: float = Field(..., description="Total tax across all points")

    class Config:
        json_schema_extra = {
            "example": {
                "chart_type": "monthly_tax",
                "data": [
                    {"date": "2025-01", "income": 18500.00, "tax": 185.00},
                    {"date": "2025-02", "income": 21000.00, "tax": 210.00}
                ],
                "total_income": 245000.00,
                "total_tax": 2450.00
            }
        }


# ========== Payment & Filing Service ==========

class PaymentRequest(BaseModel):
    """Request payment for admin filing service"""
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)


class PaymentResponse(BaseModel):
    """Mock payment confirmation"""
    declaration_id: str
    payment_id: str = Field(..., description="Mock payment ID")
    income_gel: float = Field(..., description="Total income for the month")
    tax_amount: float = Field(..., description="Tax to government (1%)")
    service_fee: float = Field(..., description="Service fee to company (configurable %)")
    total_amount: float = Field(..., description="Total payment amount (tax + service fee)")
    status: str = Field(..., description="Payment status: paid")
    paid_at: datetime
    message: str = Field(default="Payment successful. Your declaration will be filed by our admin team.")


class FilingServiceStatus(BaseModel):
    """Status of filing service for a declaration"""
    year: int
    month: int
    status: DeclarationStatus
    payment_status: str
    payment_amount: float
    payment_date: Optional[datetime]
    filing_method: str
    filed_by_admin_at: Optional[datetime] = None
    requires_correction: bool
    correction_notes: str
    admin_notes: str
