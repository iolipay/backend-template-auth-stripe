"""Admin schemas for tax declaration filing service"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.tax_declaration import DeclarationStatus


# Admin-specific declaration schemas
class DeclarationAdminUpdate(BaseModel):
    """Update declaration status (admin action)"""
    status: DeclarationStatus
    admin_notes: Optional[str] = None
    requires_correction: Optional[bool] = None
    correction_notes: Optional[str] = None


class DeclarationFilingComplete(BaseModel):
    """Mark declaration as filed by admin"""
    confirmation_number: Optional[str] = Field(None, description="RS.ge confirmation number")
    admin_notes: Optional[str] = Field(None, description="Internal notes about the filing")


class DeclarationReject(BaseModel):
    """Reject a declaration and request corrections"""
    correction_notes: str = Field(..., description="What the user needs to fix")
    admin_notes: Optional[str] = Field(None, description="Internal notes")


# Admin queue and list responses
class AdminDeclarationListItem(BaseModel):
    """Declaration item in admin queue"""
    id: str
    user_id: str
    user_email: str
    year: int
    month: int
    income_gel: float
    tax_due_gel: float
    status: DeclarationStatus
    filing_deadline: datetime
    payment_status: str
    payment_amount: float
    payment_date: Optional[datetime]
    submitted_date: Optional[datetime]
    requires_correction: bool
    transaction_count: int


class AdminDeclarationQueue(BaseModel):
    """Admin queue response"""
    pending_payment: List[AdminDeclarationListItem] = []
    ready_to_file: List[AdminDeclarationListItem] = []
    in_progress: List[AdminDeclarationListItem] = []
    needs_correction: List[AdminDeclarationListItem] = []
    total_count: int


class AdminStats(BaseModel):
    """Admin dashboard statistics"""
    total_declarations_this_month: int
    pending_payment: int
    ready_to_file: int
    in_progress: int
    filed_this_month: int
    rejected_this_month: int
    total_revenue_this_month: float  # Total payment_amount received
    average_filing_time_hours: Optional[float] = None


# User management schemas
class GrantAdminAccess(BaseModel):
    """Grant admin access to a user"""
    user_id: str


class RevokeAdminAccess(BaseModel):
    """Revoke admin access from a user"""
    user_id: str


class AdminUserListItem(BaseModel):
    """User in admin list"""
    id: str
    email: str
    is_admin: bool
    is_verified: bool
    admin_since: Optional[datetime]
    created_at: datetime
    subscription_plan: str
    total_declarations: int
    total_filed: int
    total_paid: float


class AdminAllDeclarationsResponse(BaseModel):
    """Response for all declarations across all users"""
    declarations: List[AdminDeclarationListItem]
    total_count: int
    total_revenue: float
