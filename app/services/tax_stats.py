"""
Tax Statistics Service

Manages tax calculations, projections, insights, and declarations
for Georgian small business users (1% tax rate, 500k GEL threshold)
"""

from datetime import datetime, date, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from calendar import monthrange
from bson import ObjectId
import logging

from app.schemas.tax_stats import (
    TaxOverview,
    ThresholdStatus,
    MonthlyTaxSummary,
    MonthlyTaxBreakdown,
    TaxProjection,
    ThresholdRisk,
    TaxInsight,
    TaxInsightsList,
    InsightType,
    InsightSeverity,
    YearlyTaxSummary,
    TaxComparison,
    DeclarationDetails,
    TaxChartData,
    TaxChartDataPoint
)
from app.models.tax_declaration import DeclarationStatus

logger = logging.getLogger(__name__)


class TaxStatsService:
    """Service for tax statistics and declaration management"""

    # Constants for Georgian small business tax
    TAX_RATE = 0.01  # 1%
    ANNUAL_THRESHOLD = 500000.00  # 500k GEL
    FILING_DAY = 15  # Declarations due on 15th of next month

    def __init__(self, db):
        self.db = db

    # ========== Tax Overview ==========

    async def get_tax_overview(self, user_id: str, year: Optional[int] = None) -> TaxOverview:
        """
        Get comprehensive tax overview for dashboard

        Args:
            user_id: User ID
            year: Tax year (default: current year)

        Returns:
            TaxOverview with current status
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        # Get all transactions for the year
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "transaction_date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_income": {"$sum": "$amount_gel"}
                }
            }
        ]

        result = await self.db.transactions.aggregate(pipeline).to_list(length=1)
        total_income = result[0]["total_income"] if result else 0.0
        tax_liability = total_income * self.TAX_RATE

        # Calculate threshold status
        threshold_remaining = max(0, self.ANNUAL_THRESHOLD - total_income)
        threshold_percentage = (total_income / self.ANNUAL_THRESHOLD) * 100

        if threshold_percentage < 75:
            status = ThresholdStatus.ON_TRACK
        elif threshold_percentage < 90:
            status = ThresholdStatus.APPROACHING_LIMIT
        elif threshold_percentage < 100:
            status = ThresholdStatus.NEAR_LIMIT
        else:
            status = ThresholdStatus.EXCEEDED

        # Get declaration counts
        declarations = await self.db.tax_declarations.find({
            "user_id": user_id,
            "year": year
        }).to_list(length=None)

        months_declared = sum(1 for d in declarations if d.get("status") == DeclarationStatus.SUBMITTED.value)
        months_pending = sum(1 for d in declarations if d.get("status") == DeclarationStatus.PENDING.value)

        # Get last declaration date
        last_submitted = await self.db.tax_declarations.find_one(
            {
                "user_id": user_id,
                "status": DeclarationStatus.SUBMITTED.value
            },
            sort=[("submitted_date", -1)]
        )
        last_declaration_date = last_submitted.get("submitted_date") if last_submitted else None

        # Get next deadline
        next_pending = await self.db.tax_declarations.find_one(
            {
                "user_id": user_id,
                "status": DeclarationStatus.PENDING.value
            },
            sort=[("filing_deadline", 1)]
        )
        next_declaration_due = next_pending.get("filing_deadline") if next_pending else None

        return TaxOverview(
            year=year,
            total_income_ytd_gel=round(total_income, 2),
            tax_liability_ytd_gel=round(tax_liability, 2),
            threshold_remaining_gel=round(threshold_remaining, 2),
            threshold_percentage_used=round(threshold_percentage, 2),
            status=status,
            months_declared=months_declared,
            months_pending=months_pending,
            last_declaration_date=last_declaration_date,
            next_declaration_due=next_declaration_due
        )

    # ========== Monthly Tax Breakdown ==========

    async def get_monthly_tax_breakdown(self, user_id: str, year: Optional[int] = None) -> MonthlyTaxBreakdown:
        """
        Get detailed monthly tax breakdown for a year

        Args:
            user_id: User ID
            year: Tax year (default: current year)

        Returns:
            Monthly breakdown with declaration status
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        # Get or create declarations for all months
        months_data = []
        total_income = 0.0
        total_tax = 0.0
        current_date = datetime.now(timezone.utc)

        for month in range(1, 13):
            # Get or create declaration
            declaration = await self._get_or_create_declaration(user_id, year, month)

            if declaration:
                income = declaration.get("income_gel", 0.0)
                tax = declaration.get("tax_due_gel", 0.0)
                total_income += income
                total_tax += tax

                # Calculate days until deadline
                filing_deadline = declaration["filing_deadline"]
                # Ensure timezone awareness
                if filing_deadline.tzinfo is None:
                    filing_deadline = filing_deadline.replace(tzinfo=timezone.utc)

                days_until = None
                if declaration["status"] == DeclarationStatus.PENDING.value and filing_deadline > current_date:
                    days_until = (filing_deadline - current_date).days

                months_data.append(MonthlyTaxSummary(
                    month=f"{year}-{month:02d}",
                    income_gel=round(income, 2),
                    tax_due_gel=round(tax, 2),
                    declaration_status=declaration["status"],
                    filing_deadline=filing_deadline,
                    submitted_date=declaration.get("submitted_date"),
                    days_until_deadline=days_until,
                    transaction_count=declaration.get("transaction_count", 0)
                ))

        avg_monthly_income = total_income / len([m for m in months_data if m.income_gel > 0]) if months_data else 0.0
        avg_monthly_tax = total_tax / len([m for m in months_data if m.tax_due_gel > 0]) if months_data else 0.0

        return MonthlyTaxBreakdown(
            year=year,
            months=months_data,
            total_income_gel=round(total_income, 2),
            total_tax_gel=round(total_tax, 2),
            avg_monthly_income_gel=round(avg_monthly_income, 2),
            avg_monthly_tax_gel=round(avg_monthly_tax, 2)
        )

    # ========== Tax Projections ==========

    async def get_tax_projections(self, user_id: str) -> TaxProjection:
        """
        Generate forward-looking tax projections

        Args:
            user_id: User ID

        Returns:
            Projected annual income and tax
        """
        current_year = datetime.now(timezone.utc).year
        current_month = datetime.now(timezone.utc).month

        # Get YTD income
        start_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "transaction_date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_income": {"$sum": "$amount_gel"}
                }
            }
        ]

        result = await self.db.transactions.aggregate(pipeline).to_list(length=1)
        current_income = result[0]["total_income"] if result else 0.0
        current_tax = current_income * self.TAX_RATE

        # Project annual income
        months_elapsed = current_month
        if months_elapsed > 0 and current_income > 0:
            monthly_avg = current_income / months_elapsed
            projected_annual_income = monthly_avg * 12
        else:
            projected_annual_income = 0.0

        projected_annual_tax = projected_annual_income * self.TAX_RATE

        # Assess threshold risk
        will_exceed = projected_annual_income > self.ANNUAL_THRESHOLD
        projected_remaining = max(0, self.ANNUAL_THRESHOLD - projected_annual_income)

        # Calculate risk level
        threshold_percentage = (projected_annual_income / self.ANNUAL_THRESHOLD) * 100
        if threshold_percentage < 75:
            risk_level = "low"
            confidence = 0.85
        elif threshold_percentage < 90:
            risk_level = "medium"
            confidence = 0.75
        elif threshold_percentage < 100:
            risk_level = "high"
            confidence = 0.70
        else:
            risk_level = "high"
            confidence = 0.80

        threshold_status = ThresholdRisk(
            will_exceed_threshold=will_exceed,
            threshold_gel=self.ANNUAL_THRESHOLD,
            projected_remaining_gel=round(projected_remaining, 2),
            risk_level=risk_level,
            confidence=confidence
        )

        # Generate recommendation
        if will_exceed:
            recommendation = f"Projected to exceed threshold by {round(projected_annual_income - self.ANNUAL_THRESHOLD, 2):,.0f} GEL. Consider consulting an accountant."
        elif threshold_percentage > 85:
            recommendation = f"Approaching threshold. You have {round(projected_remaining, 2):,.0f} GEL remaining capacity this year."
        else:
            recommendation = "You're on track. Current pace keeps you under the 500k limit."

        # Monthly average needed to reach threshold
        months_remaining = 12 - current_month
        if months_remaining > 0:
            monthly_avg_needed = (self.ANNUAL_THRESHOLD - current_income) / months_remaining
        else:
            monthly_avg_needed = 0.0

        return TaxProjection(
            based_on_months=months_elapsed,
            current_income_gel=round(current_income, 2),
            current_tax_gel=round(current_tax, 2),
            projected_annual_income_gel=round(projected_annual_income, 2),
            projected_annual_tax_gel=round(projected_annual_tax, 2),
            threshold_status=threshold_status,
            monthly_avg_needed_for_threshold=round(monthly_avg_needed, 2),
            recommendation=recommendation
        )

    # ========== Tax Insights ==========

    async def get_tax_insights(self, user_id: str) -> TaxInsightsList:
        """
        Generate smart insights and alerts

        Args:
            user_id: User ID

        Returns:
            List of actionable insights
        """
        insights = []
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year

        # Check for upcoming deadlines
        pending_declarations = await self.db.tax_declarations.find({
            "user_id": user_id,
            "status": DeclarationStatus.PENDING.value,
            "filing_deadline": {"$gte": current_date}
        }).sort("filing_deadline", 1).to_list(length=None)

        for decl in pending_declarations:
            filing_deadline = decl["filing_deadline"]
            # Ensure timezone awareness
            if filing_deadline.tzinfo is None:
                filing_deadline = filing_deadline.replace(tzinfo=timezone.utc)

            days_until = (filing_deadline - current_date).days

            if days_until <= 1:
                severity = InsightSeverity.CRITICAL
                title = "Declaration Due Tomorrow!"
            elif days_until <= 3:
                severity = InsightSeverity.HIGH
                title = f"Declaration Due in {days_until} Days"
            elif days_until <= 7:
                severity = InsightSeverity.MEDIUM
                title = f"Declaration Due in {days_until} Days"
            else:
                continue  # Don't show insights for far future

            month_name = datetime(decl["year"], decl["month"], 1).strftime("%B %Y")
            insights.append(TaxInsight(
                type=InsightType.DECLARATION_REMINDER,
                severity=severity,
                title=title,
                message=f"Your {month_name} declaration is due on {decl['filing_deadline'].strftime('%B %d')}. Income: {decl['income_gel']:,.2f} GEL, Tax: {decl['tax_due_gel']:,.2f} GEL",
                action_url=f"/tax-stats/declarations/{decl['year']}/{decl['month']}",
                action_text="Prepare Declaration",
                action_required=True,
                created_at=current_date
            ))

        # Check for overdue declarations
        overdue_declarations = await self.db.tax_declarations.find({
            "user_id": user_id,
            "status": DeclarationStatus.PENDING.value,
            "filing_deadline": {"$lt": current_date}
        }).to_list(length=None)

        if overdue_declarations:
            insights.append(TaxInsight(
                type=InsightType.COMPLIANCE_ALERT,
                severity=InsightSeverity.CRITICAL,
                title=f"{len(overdue_declarations)} Overdue Declaration(s)",
                message=f"You have {len(overdue_declarations)} overdue tax declaration(s). File immediately to avoid penalties.",
                action_required=True,
                created_at=current_date
            ))

        # Check threshold status
        overview = await self.get_tax_overview(user_id, current_year)

        if overview.threshold_percentage_used >= 95:
            insights.append(TaxInsight(
                type=InsightType.THRESHOLD_WARNING,
                severity=InsightSeverity.CRITICAL,
                title="Near Annual Threshold Limit",
                message=f"You've used {overview.threshold_percentage_used:.1f}% of your 500k annual limit. Only {overview.threshold_remaining_gel:,.0f} GEL remaining. Consult an accountant.",
                action_required=False,
                created_at=current_date
            ))
        elif overview.threshold_percentage_used >= 85:
            insights.append(TaxInsight(
                type=InsightType.THRESHOLD_WARNING,
                severity=InsightSeverity.HIGH,
                title="Approaching Annual Threshold",
                message=f"You've used {overview.threshold_percentage_used:.1f}% of your 500k annual limit. Plan accordingly for remaining months.",
                action_required=False,
                created_at=current_date
            ))
        elif overview.threshold_percentage_used >= 75:
            insights.append(TaxInsight(
                type=InsightType.THRESHOLD_WARNING,
                severity=InsightSeverity.MEDIUM,
                title="75% of Annual Threshold Reached",
                message=f"You've reached 75% of your annual limit. {overview.threshold_remaining_gel:,.0f} GEL remaining for the year.",
                action_required=False,
                created_at=current_date
            ))

        # Check for income spikes or drops (compare last month to average)
        if current_date.month > 1:
            last_month = current_date.month - 1
            last_month_decl = await self.db.tax_declarations.find_one({
                "user_id": user_id,
                "year": current_year,
                "month": last_month
            })

            if last_month_decl and last_month_decl.get("income_gel", 0) > 0:
                # Get average of previous months
                avg_pipeline = [
                    {
                        "$match": {
                            "user_id": user_id,
                            "year": current_year,
                            "month": {"$lt": last_month}
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "avg_income": {"$avg": "$income_gel"}
                        }
                    }
                ]

                avg_result = await self.db.tax_declarations.aggregate(avg_pipeline).to_list(length=1)
                if avg_result and avg_result[0].get("avg_income", 0) > 0:
                    avg_income = avg_result[0]["avg_income"]
                    last_income = last_month_decl["income_gel"]
                    change_percent = ((last_income - avg_income) / avg_income) * 100

                    if change_percent > 30:
                        insights.append(TaxInsight(
                            type=InsightType.INCOME_SPIKE,
                            severity=InsightSeverity.INFO,
                            title=f"Income Increased {change_percent:.0f}% Last Month",
                            message=f"Your {datetime(current_year, last_month, 1).strftime('%B')} income was {change_percent:.0f}% higher than your average. Great month!",
                            action_required=False,
                            created_at=current_date
                        ))
                    elif change_percent < -30:
                        insights.append(TaxInsight(
                            type=InsightType.INCOME_DROP,
                            severity=InsightSeverity.INFO,
                            title=f"Income Decreased {abs(change_percent):.0f}% Last Month",
                            message=f"Your {datetime(current_year, last_month, 1).strftime('%B')} income was {abs(change_percent):.0f}% lower than your average.",
                            action_required=False,
                            created_at=current_date
                        ))

        # Add optimization tip if applicable
        if overview.threshold_remaining_gel > 100000:
            insights.append(TaxInsight(
                type=InsightType.OPTIMIZATION_TIP,
                severity=InsightSeverity.INFO,
                title="Room for Growth",
                message=f"You have {overview.threshold_remaining_gel:,.0f} GEL remaining capacity this year. Consider taking on additional projects.",
                action_required=False,
                created_at=current_date
            ))

        # Sort by severity
        severity_order = {
            InsightSeverity.CRITICAL: 0,
            InsightSeverity.HIGH: 1,
            InsightSeverity.MEDIUM: 2,
            InsightSeverity.INFO: 3
        }
        insights.sort(key=lambda x: severity_order[x.severity])

        high_priority_count = sum(
            1 for i in insights
            if i.severity in [InsightSeverity.HIGH, InsightSeverity.CRITICAL]
        )

        return TaxInsightsList(
            insights=insights,
            total_insights=len(insights),
            high_priority_count=high_priority_count
        )

    # ========== Year-over-Year Comparison ==========

    async def get_tax_comparison(self, user_id: str, years: List[int]) -> TaxComparison:
        """
        Compare tax data across multiple years

        Args:
            user_id: User ID
            years: List of years to compare (max 5)

        Returns:
            Year-over-year comparison
        """
        years = sorted(years[:5], reverse=True)  # Limit to 5 years, newest first
        yearly_summaries = []
        total_tax_all_years = 0.0

        previous_income = None

        for year in years:
            # Get declarations for the year
            declarations = await self.db.tax_declarations.find({
                "user_id": user_id,
                "year": year
            }).to_list(length=None)

            total_income = sum(d.get("income_gel", 0) for d in declarations)
            total_tax = sum(d.get("tax_due_gel", 0) for d in declarations)
            months_with_income = sum(1 for d in declarations if d.get("income_gel", 0) > 0)

            avg_monthly = total_income / months_with_income if months_with_income > 0 else 0.0

            # Calculate growth vs previous year
            growth = None
            if previous_income is not None and previous_income > 0:
                growth = ((total_income - previous_income) / previous_income) * 100

            yearly_summaries.append(YearlyTaxSummary(
                year=year,
                total_income_gel=round(total_income, 2),
                total_tax_gel=round(total_tax, 2),
                avg_monthly_income_gel=round(avg_monthly, 2),
                months_with_income=months_with_income,
                growth_vs_previous=round(growth, 2) if growth is not None else None
            ))

            total_tax_all_years += total_tax
            previous_income = total_income

        return TaxComparison(
            years=yearly_summaries,
            total_tax_paid_all_years=round(total_tax_all_years, 2)
        )

    # ========== Declaration Management ==========

    async def get_declaration_details(self, user_id: str, year: int, month: int) -> Optional[DeclarationDetails]:
        """Get detailed information for a specific declaration"""
        declaration = await self._get_or_create_declaration(user_id, year, month)

        if not declaration:
            return None

        current_date = datetime.now(timezone.utc)
        filing_deadline = declaration["filing_deadline"]
        # Ensure timezone awareness
        if filing_deadline.tzinfo is None:
            filing_deadline = filing_deadline.replace(tzinfo=timezone.utc)

        days_until = None
        is_overdue = False

        if declaration["status"] == DeclarationStatus.PENDING.value:
            if filing_deadline < current_date:
                is_overdue = True
            else:
                days_until = (filing_deadline - current_date).days

        month_name = datetime(year, month, 1).strftime("%B %Y")

        return DeclarationDetails(
            year=year,
            month=month,
            month_name=month_name,
            income_gel=round(declaration["income_gel"], 2),
            tax_due_gel=round(declaration["tax_due_gel"], 2),
            transaction_count=declaration["transaction_count"],
            declaration_status=declaration["status"],
            filing_deadline=filing_deadline,
            submitted_date=declaration.get("submitted_date"),
            days_until_deadline=days_until,
            is_overdue=is_overdue
        )

    async def mark_declaration_submitted(
        self,
        user_id: str,
        year: int,
        month: int,
        submitted_date: Optional[datetime] = None
    ) -> bool:
        """
        Mark a declaration as submitted

        Args:
            user_id: User ID
            year: Year
            month: Month
            submitted_date: Submission date (defaults to now)

        Returns:
            True if successful
        """
        if submitted_date is None:
            submitted_date = datetime.now(timezone.utc)

        result = await self.db.tax_declarations.update_one(
            {
                "user_id": user_id,
                "year": year,
                "month": month
            },
            {
                "$set": {
                    "status": DeclarationStatus.SUBMITTED.value,
                    "submitted_date": submitted_date,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return result.modified_count > 0

    # ========== Chart Data ==========

    async def get_tax_chart_data(
        self,
        user_id: str,
        chart_type: str,
        year: Optional[int] = None
    ) -> TaxChartData:
        """
        Get chart data for visualizations

        Args:
            user_id: User ID
            chart_type: Type of chart (monthly_tax, cumulative_tax, threshold_progress)
            year: Year (default: current)

        Returns:
            Chart data
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        declarations = await self.db.tax_declarations.find({
            "user_id": user_id,
            "year": year
        }).sort("month", 1).to_list(length=None)

        data_points = []
        total_income = 0.0
        total_tax = 0.0
        cumulative_income = 0.0

        for decl in declarations:
            if decl.get("income_gel", 0) <= 0:
                continue

            income = decl["income_gel"]
            tax = decl["tax_due_gel"]
            month_str = f"{year}-{decl['month']:02d}"

            total_income += income
            total_tax += tax

            if chart_type == "cumulative_tax":
                cumulative_income += income
                data_points.append(TaxChartDataPoint(
                    date=month_str,
                    income=round(cumulative_income, 2),
                    tax=round(cumulative_income * self.TAX_RATE, 2)
                ))
            else:
                data_points.append(TaxChartDataPoint(
                    date=month_str,
                    income=round(income, 2),
                    tax=round(tax, 2)
                ))

        return TaxChartData(
            chart_type=chart_type,
            data=data_points,
            total_income=round(total_income, 2),
            total_tax=round(total_tax, 2)
        )

    # ========== Helper Methods ==========

    async def _get_or_create_declaration(self, user_id: str, year: int, month: int) -> Optional[Dict[str, Any]]:
        """
        Get existing declaration or create new one

        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)

        Returns:
            Declaration document
        """
        # Check if declaration exists
        existing = await self.db.tax_declarations.find_one({
            "user_id": user_id,
            "year": year,
            "month": month
        })

        if existing:
            # Update status if overdue
            if existing["status"] == DeclarationStatus.PENDING.value:
                filing_deadline = existing["filing_deadline"]
                # Ensure timezone awareness
                if filing_deadline.tzinfo is None:
                    filing_deadline = filing_deadline.replace(tzinfo=timezone.utc)

                if filing_deadline < datetime.now(timezone.utc):
                    await self.db.tax_declarations.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"status": DeclarationStatus.OVERDUE.value}}
                    )
                    existing["status"] = DeclarationStatus.OVERDUE.value

            return existing

        # Calculate income for the month
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "transaction_date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_income": {"$sum": "$amount_gel"},
                    "count": {"$sum": 1},
                    "transaction_ids": {"$push": {"$toString": "$_id"}}
                }
            }
        ]

        result = await self.db.transactions.aggregate(pipeline).to_list(length=1)

        if result:
            income = result[0]["total_income"]
            count = result[0]["count"]
            transaction_ids = result[0]["transaction_ids"]
        else:
            income = 0.0
            count = 0
            transaction_ids = []

        # Calculate filing deadline (15th of next month)
        if month == 12:
            deadline_year = year + 1
            deadline_month = 1
        else:
            deadline_year = year
            deadline_month = month + 1

        filing_deadline = datetime(deadline_year, deadline_month, self.FILING_DAY, 23, 59, 59, tzinfo=timezone.utc)

        # Determine initial status
        current_date = datetime.now(timezone.utc)
        if filing_deadline < current_date:
            status = DeclarationStatus.OVERDUE.value if income > 0 else DeclarationStatus.PENDING.value
        else:
            status = DeclarationStatus.PENDING.value

        # Create declaration
        declaration_doc = {
            "user_id": user_id,
            "year": year,
            "month": month,
            "income_gel": income,
            "tax_due_gel": income * self.TAX_RATE,
            "transaction_count": count,
            "transaction_ids": transaction_ids,
            "status": status,
            "filing_deadline": filing_deadline,
            "submitted_date": None,
            "auto_generated_at": current_date,
            "created_at": current_date,
            "updated_at": current_date
        }

        result = await self.db.tax_declarations.insert_one(declaration_doc)
        declaration_doc["_id"] = result.inserted_id

        logger.info(f"Created tax declaration for user {user_id}, {year}-{month:02d}")
        return declaration_doc

    async def auto_generate_declarations(self, user_id: str, year: Optional[int] = None):
        """
        Auto-generate declarations for all months in a year

        Args:
            user_id: User ID
            year: Year (default: current year)
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        for month in range(1, 13):
            await self._get_or_create_declaration(user_id, year, month)

        logger.info(f"Auto-generated declarations for user {user_id}, year {year}")
