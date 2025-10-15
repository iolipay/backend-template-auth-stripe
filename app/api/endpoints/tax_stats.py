from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from app.api.deps import get_current_user, get_tax_stats_service
from app.schemas.user import UserResponse
from app.schemas.tax_stats import (
    TaxOverview,
    MonthlyTaxBreakdown,
    TaxProjection,
    TaxInsightsList,
    TaxComparison,
    DeclarationDetails,
    MarkDeclarationRequest,
    MarkDeclarationResponse,
    TaxChartData,
    PaymentRequest,
    PaymentResponse,
    FilingServiceStatus
)
from app.services.tax_stats import TaxStatsService
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tax Statistics"])


@router.get(
    "/overview",
    response_model=TaxOverview,
    description="Get comprehensive tax overview for dashboard"
)
async def get_tax_overview(
    year: Optional[int] = Query(None, description="Tax year (default: current year)"),
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> TaxOverview:
    """
    Get tax overview including:
    - Year-to-date income and tax liability
    - Threshold usage (% of 500k limit)
    - Declaration status (submitted/pending)
    - Next deadline

    Perfect for dashboard summary card.
    """
    try:
        overview = await tax_service.get_tax_overview(current_user.id, year)
        return overview
    except Exception as e:
        logger.error(f"Error getting tax overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tax overview")


@router.get(
    "/monthly",
    response_model=MonthlyTaxBreakdown,
    description="Get monthly tax breakdown for a year"
)
async def get_monthly_tax_breakdown(
    year: Optional[int] = Query(None, description="Tax year (default: current year)"),
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> MonthlyTaxBreakdown:
    """
    Get detailed monthly breakdown including:
    - Income and tax for each month
    - Declaration status (pending/submitted/overdue)
    - Filing deadlines
    - Days until deadline
    - Transaction counts

    Use this for monthly tax table/calendar view.
    """
    try:
        breakdown = await tax_service.get_monthly_tax_breakdown(current_user.id, year)
        return breakdown
    except Exception as e:
        logger.error(f"Error getting monthly breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monthly breakdown")


@router.get(
    "/projections",
    response_model=TaxProjection,
    description="Get forward-looking tax projections"
)
async def get_tax_projections(
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> TaxProjection:
    """
    Get tax projections based on current year performance:
    - Projected annual income and tax
    - Threshold risk assessment
    - Confidence scores
    - Personalized recommendations

    Use this for "What if" scenarios and planning.
    """
    try:
        projections = await tax_service.get_tax_projections(current_user.id)
        return projections
    except Exception as e:
        logger.error(f"Error getting projections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get projections")


@router.get(
    "/insights",
    response_model=TaxInsightsList,
    description="Get smart tax insights and alerts"
)
async def get_tax_insights(
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> TaxInsightsList:
    """
    Get intelligent insights including:
    - Upcoming declaration deadlines (7, 3, 1 day alerts)
    - Threshold warnings (75%, 85%, 95%)
    - Income pattern changes (spikes, drops)
    - Optimization tips
    - Compliance alerts (overdue declarations)

    Sorted by priority (critical > high > medium > info).
    """
    try:
        insights = await tax_service.get_tax_insights(current_user.id)
        return insights
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get insights")


@router.get(
    "/comparison",
    response_model=TaxComparison,
    description="Get year-over-year tax comparison"
)
async def get_tax_comparison(
    years: str = Query(..., description="Comma-separated years (e.g., '2025,2024,2023'), max 5"),
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> TaxComparison:
    """
    Compare tax data across multiple years:
    - Total income and tax per year
    - Average monthly income
    - Year-over-year growth percentages
    - Total tax paid across all years

    Example: /tax-stats/comparison?years=2025,2024,2023
    """
    try:
        # Parse years
        year_list = [int(y.strip()) for y in years.split(",")]
        if len(year_list) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 years allowed")

        comparison = await tax_service.get_tax_comparison(current_user.id, year_list)
        return comparison
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid year format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comparison")


@router.get(
    "/declarations/{year}/{month}",
    response_model=DeclarationDetails,
    description="Get details for a specific declaration"
)
async def get_declaration_details(
    year: int,
    month: int,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> DeclarationDetails:
    """
    Get detailed information for a specific month's declaration:
    - Income and tax amounts
    - Transaction count
    - Declaration status
    - Filing deadline
    - Days until deadline or overdue status

    Use this when user clicks on a specific month to prepare declaration.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    try:
        details = await tax_service.get_declaration_details(current_user.id, year, month)
        if not details:
            raise HTTPException(status_code=404, detail="Declaration not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting declaration details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get declaration details")


@router.post(
    "/declarations/{year}/{month}/mark-submitted",
    response_model=MarkDeclarationResponse,
    description="Mark a declaration as submitted"
)
async def mark_declaration_submitted(
    year: int,
    month: int,
    request: MarkDeclarationRequest,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> MarkDeclarationResponse:
    """
    Mark a declaration as submitted after user files it on rs.ge.

    Updates declaration status and records submission date.
    This helps track compliance and removes pending alerts.

    Request body:
    ```json
    {
      "submitted_date": "2025-11-05T10:30:00Z"  // Optional, defaults to now
    }
    ```
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    try:
        # Mark as submitted
        success = await tax_service.mark_declaration_submitted(
            current_user.id,
            year,
            month,
            request.submitted_date
        )

        if not success:
            raise HTTPException(status_code=404, detail="Declaration not found")

        # Get updated details
        details = await tax_service.get_declaration_details(current_user.id, year, month)

        return MarkDeclarationResponse(
            success=True,
            message=f"Declaration for {details.month_name} marked as submitted",
            declaration=details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking declaration submitted: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark declaration as submitted")


@router.get(
    "/charts/{chart_type}",
    response_model=TaxChartData,
    description="Get chart data for visualizations"
)
async def get_tax_chart_data(
    chart_type: str,
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> TaxChartData:
    """
    Get time-series data for charts.

    Chart types:
    - **monthly_tax**: Monthly income and tax amounts
    - **cumulative_tax**: Cumulative income and tax over the year
    - **threshold_progress**: Progress toward 500k threshold

    Returns array of data points with date, income, and tax.
    Perfect for line charts, bar charts, or area charts.

    Example: /tax-stats/charts/monthly_tax?year=2025
    """
    valid_types = ["monthly_tax", "cumulative_tax", "threshold_progress"]
    if chart_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chart_type. Must be one of: {', '.join(valid_types)}"
        )

    try:
        chart_data = await tax_service.get_tax_chart_data(
            current_user.id,
            chart_type,
            year
        )
        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chart data")


@router.post(
    "/auto-generate/{year}",
    status_code=200,
    description="Auto-generate declarations for all months in a year"
)
async def auto_generate_declarations(
    year: int,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Manually trigger auto-generation of declarations for all months.

    Useful for:
    - Initial setup
    - Recalculating after adding past transactions
    - Fixing missing declarations

    This is also done automatically when user accesses monthly breakdown.
    """
    try:
        await tax_service.auto_generate_declarations(current_user.id, year)
        return {
            "success": True,
            "message": f"Auto-generated declarations for {year}"
        }
    except Exception as e:
        logger.error(f"Error auto-generating declarations: {e}")
        raise HTTPException(status_code=500, detail="Failed to auto-generate declarations")


# ========== Payment & Filing Service Endpoints ==========

@router.post(
    "/filing-service/request",
    description="Request admin filing service for a declaration"
)
async def request_filing_service(
    payment_request: PaymentRequest,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Request admin filing service for a specific declaration.

    This transitions the declaration to AWAITING_PAYMENT status.

    User will then need to call the payment endpoint to complete payment.
    """
    try:
        result = await tax_service.request_filing_service(
            current_user.id,
            payment_request.year,
            payment_request.month
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error requesting filing service: {e}")
        raise HTTPException(status_code=500, detail="Failed to request filing service")


@router.post(
    "/filing-service/pay",
    response_model=PaymentResponse,
    description="Process mock payment for filing service"
)
async def pay_for_filing_service(
    payment_request: PaymentRequest,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> PaymentResponse:
    """
    Process mock payment for admin filing service.

    **MOCK PAYMENT ONLY** - This simulates payment processing.

    After payment:
    - Declaration moves to PAYMENT_RECEIVED status
    - Declaration enters admin queue
    - Admin team will file the declaration on RS.ge

    Fee: 50 GEL per declaration
    """
    try:
        result = await tax_service.process_mock_payment(
            current_user.id,
            payment_request.year,
            payment_request.month
        )
        return PaymentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to process payment")


@router.get(
    "/filing-service/status/{year}/{month}",
    response_model=FilingServiceStatus,
    description="Get filing service status for a declaration"
)
async def get_filing_service_status(
    year: int,
    month: int,
    current_user: UserResponse = Depends(get_current_user),
    tax_service: TaxStatsService = Depends(get_tax_stats_service)
) -> FilingServiceStatus:
    """
    Get the status of filing service for a specific declaration.

    Returns:
    - Payment status (paid/unpaid)
    - Declaration status (pending, awaiting_payment, payment_received, in_progress, filed_by_admin, rejected)
    - Admin notes (if any)
    - Correction notes (if rejected and needs fixing)
    """
    try:
        result = await tax_service.get_filing_service_status(
            current_user.id,
            year,
            month
        )
        return FilingServiceStatus(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting filing service status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get filing service status")
