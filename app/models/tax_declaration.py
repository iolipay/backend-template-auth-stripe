from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


class DeclarationStatus(str, Enum):
    """Status of tax declaration submission"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    OVERDUE = "overdue"


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
    auto_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
