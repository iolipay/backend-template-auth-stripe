from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


class DeclarationStatus(str, Enum):
    """Status of tax declaration submission"""
    PENDING = "pending"  # Self-service: User hasn't filed yet
    SUBMITTED = "submitted"  # Self-service: User filed themselves
    OVERDUE = "overdue"  # Self-service: Deadline passed, not filed

    # Admin filing service statuses
    AWAITING_PAYMENT = "awaiting_payment"  # User requested filing service, needs to pay
    PAYMENT_RECEIVED = "payment_received"  # Paid, in admin queue
    IN_PROGRESS = "in_progress"  # Admin currently filing
    FILED_BY_ADMIN = "filed_by_admin"  # Successfully filed by admin
    REJECTED = "rejected"  # Admin rejected, needs corrections


class TaxDeclaration(BaseModel):
    """
    Tax declaration record for a specific month

    Tracks the declaration status for Georgian small business tax (1% rate)
    """
    id: str
    user_id: str

    # Period information
    year: int = Field(..., description="Year of the declaration")
    month: int = Field(..., ge=1, le=12, description="Month of the declaration (1-12)")

    # Financial data
    income_gel: float = Field(..., description="Total income for the month in GEL")
    tax_due_gel: float = Field(..., description="Tax amount due (1% of income)")
    transaction_count: int = Field(default=0, description="Number of transactions included")
    transaction_ids: List[str] = Field(default_factory=list, description="IDs of transactions included")

    # Declaration status
    status: DeclarationStatus = Field(default=DeclarationStatus.PENDING, description="Current status")
    filing_deadline: datetime = Field(..., description="Deadline for filing (15th of next month)")

    # Submission tracking
    submitted_date: Optional[datetime] = Field(None, description="Date when declaration was submitted")

    # Payment tracking (MOCK)
    payment_status: str = Field(default="unpaid", description="Payment status: unpaid, paid, refunded")
    payment_amount: float = Field(default=50.00, description="Filing service fee amount")
    payment_date: Optional[datetime] = Field(None, description="When payment was made")
    mock_payment_id: Optional[str] = Field(None, description="Mock payment ID")

    # Admin filing tracking
    filing_method: str = Field(default="self_service", description="self_service or admin_filed")
    filed_by_admin_id: Optional[str] = Field(None, description="Admin user ID who filed")
    filed_by_admin_at: Optional[datetime] = Field(None, description="When admin filed")
    admin_notes: str = Field(default="", description="Internal notes for admins")
    requires_correction: bool = Field(default=False, description="Whether user needs to fix data")
    correction_notes: str = Field(default="", description="What user needs to fix")

    # Metadata
    auto_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaxDeclarationInDB(BaseModel):
    """Database model for tax declaration"""
    user_id: str
    year: int
    month: int
    income_gel: float
    tax_due_gel: float
    transaction_count: int = 0
    transaction_ids: List[str] = []
    status: DeclarationStatus = DeclarationStatus.PENDING
    filing_deadline: datetime
    submitted_date: Optional[datetime] = None

    # Payment tracking (MOCK)
    payment_status: str = "unpaid"
    payment_amount: float = 50.00
    payment_date: Optional[datetime] = None
    mock_payment_id: Optional[str] = None

    # Admin filing tracking
    filing_method: str = "self_service"
    filed_by_admin_id: Optional[str] = None
    filed_by_admin_at: Optional[datetime] = None
    admin_notes: str = ""
    requires_correction: bool = False
    correction_notes: str = ""

    auto_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
