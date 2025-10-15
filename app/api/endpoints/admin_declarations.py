"""Admin endpoints for tax declaration filing service"""

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional
from app.api.deps import get_current_user, get_tax_stats_service
from app.schemas.user import UserResponse
from app.schemas.admin import (
    AdminDeclarationQueue,
    DeclarationAdminUpdate,
    DeclarationFilingComplete,
    DeclarationReject,
    AdminStats,
    AdminAllDeclarationsResponse,
    AdminDeclarationListItem,
    AdminUserListItem
)
from app.services.tax_stats import TaxStatsService
from app.core.admin import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin - Tax Declarations"])


@router.get(
    "/queue",
    response_model=AdminDeclarationQueue,
    description="Get admin filing queue (requires admin privileges)"
)
@require_admin
async def get_admin_queue(
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
) -> AdminDeclarationQueue:
    """
    Get admin filing queue with declarations organized by status:
    - pending_payment: Users who requested service but haven't paid yet
    - ready_to_file: Paid declarations waiting for admin to start filing
    - in_progress: Declarations currently being filed by admins
    - needs_correction: Rejected declarations requiring user corrections
    """
    try:
        queue = await tax_stats_service.get_admin_queue()
        return AdminDeclarationQueue(**queue)
    except Exception as e:
        logger.error(f"Error getting admin queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin queue")


@router.post(
    "/{declaration_id}/start",
    description="Start filing a declaration (marks as in_progress)"
)
@require_admin
async def start_filing(
    declaration_id: str = Path(..., description="Declaration ID"),
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Admin starts filing a declaration.

    Transitions: PAYMENT_RECEIVED -> IN_PROGRESS
    """
    try:
        result = await tax_stats_service.admin_start_filing(declaration_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting declaration filing: {e}")
        raise HTTPException(status_code=500, detail="Failed to start filing")


@router.post(
    "/{declaration_id}/complete",
    description="Complete filing a declaration (marks as filed)"
)
@require_admin
async def complete_filing(
    filing_data: DeclarationFilingComplete,
    declaration_id: str = Path(..., description="Declaration ID"),
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Admin completes filing a declaration.

    Transitions: IN_PROGRESS -> FILED_BY_ADMIN

    Optionally include:
    - RS.ge confirmation number
    - Internal admin notes
    """
    try:
        result = await tax_stats_service.admin_complete_filing(
            declaration_id,
            current_user.id,
            confirmation_number=filing_data.confirmation_number,
            admin_notes=filing_data.admin_notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing declaration filing: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete filing")


@router.post(
    "/{declaration_id}/reject",
    description="Reject a declaration and request corrections"
)
@require_admin
async def reject_declaration(
    reject_data: DeclarationReject,
    declaration_id: str = Path(..., description="Declaration ID"),
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Admin rejects a declaration and requests corrections from user.

    Transitions: PAYMENT_RECEIVED or IN_PROGRESS -> REJECTED

    User will see correction_notes and must fix their transaction data.
    """
    try:
        result = await tax_stats_service.admin_reject_declaration(
            declaration_id,
            current_user.id,
            correction_notes=reject_data.correction_notes,
            admin_notes=reject_data.admin_notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting declaration: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject declaration")


@router.get(
    "/stats",
    response_model=AdminStats,
    description="Get admin dashboard statistics"
)
@require_admin
async def get_admin_stats(
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
) -> AdminStats:
    """
    Get admin dashboard statistics including:
    - Total declarations this month
    - Count by status (pending payment, ready to file, in progress, filed, rejected)
    - Total revenue this month (sum of payment_amount)
    - Average filing time
    """
    try:
        stats = await tax_stats_service.get_real_admin_stats()
        return AdminStats(**stats)
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin stats")


@router.get(
    "/all",
    response_model=AdminAllDeclarationsResponse,
    description="View all declarations from all users (admin only)"
)
@require_admin
async def get_all_declarations(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
) -> AdminAllDeclarationsResponse:
    """
    Get all declarations across all users with optional filtering.

    Query Parameters:
    - status: Filter by declaration status (pending, awaiting_payment, payment_received, etc.)
    - user_id: Filter by specific user ID
    - year: Filter by year
    - month: Filter by month (1-12)
    - limit: Max results (default 100)
    - skip: Pagination offset (default 0)

    Returns all declarations with user email, payment status, and filing status.
    """
    try:
        result = await tax_stats_service.get_all_declarations(
            status=status,
            user_id=user_id,
            year=year,
            month=month,
            limit=limit,
            skip=skip
        )
        return AdminAllDeclarationsResponse(**result)
    except Exception as e:
        logger.error(f"Error getting all declarations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get declarations")


@router.get(
    "/user/{user_id}/declarations",
    description="View all declarations for a specific user (admin only)"
)
@require_admin
async def get_user_declarations(
    user_id: str = Path(..., description="User ID"),
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Get all declarations for a specific user.

    Returns complete declaration history for the user including:
    - All months/years
    - Payment status
    - Filing status
    - Transaction counts
    """
    try:
        declarations = await tax_stats_service.get_user_declarations(user_id)
        return {"declarations": declarations, "user_id": user_id, "total_count": len(declarations)}
    except Exception as e:
        logger.error(f"Error getting user declarations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user declarations")


@router.get(
    "/users/list",
    description="List all users in the system (admin only)"
)
@require_admin
async def list_all_users(
    current_user: UserResponse = Depends(get_current_user),
    tax_stats_service: TaxStatsService = Depends(get_tax_stats_service)
):
    """
    Get list of all users with their declaration statistics.

    Returns for each user:
    - Email and basic info
    - Admin status
    - Total declarations
    - Total filed declarations
    - Total paid (sum of filing fees)
    """
    try:
        users = await tax_stats_service.get_all_users()
        return {"users": users, "total_count": len(users)}
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")
