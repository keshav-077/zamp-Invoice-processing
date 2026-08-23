from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import Decision, MatchStatus, ReasonCode, RunStage, RunStatus, UserRole


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    username: str


class RunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus
    created_at: datetime


class RunSummary(BaseModel):
    run_id: str
    status: RunStatus
    decision: Decision | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    total: Decimal | None = None
    currency: str | None = None
    po_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    processing_time_ms: int | None = None
    reason_codes: list[str] = Field(default_factory=list)


class RunDetail(BaseModel):
    run_id: str
    status: RunStatus
    current_stage: RunStage | None = None
    decision: Decision | None = None
    automated_decision: Decision | None = None
    reason_codes: list[str] = Field(default_factory=list)
    human_reason: str | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    total: Decimal | None = None
    currency: str | None = None
    po_id: str | None = None
    match_status: MatchStatus | None = None
    match_result: dict[str, Any] | None = None
    file_name: str | None = None
    page_count: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    processing_time_ms: int | None = None
    error_message: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    extraction: dict[str, Any] | None = None
    model_metadata: dict[str, Any] | None = None
    normalized_invoice: dict[str, Any] | None = None
    vendor_resolution: dict[str, Any] | None = None
    po_candidates: list[dict[str, Any]] = Field(default_factory=list)
    validation_checks: list[dict[str, Any]] = Field(default_factory=list)
    duplicate_matches: list[dict[str, Any]] = Field(default_factory=list)
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    action: str  # select_po | override_decision
    po_id: str | None = None
    decision: Decision | None = None
    reason: str


class VendorOut(BaseModel):
    vendor_id: str
    legal_name: str
    aliases: list[str] = Field(default_factory=list)
    tax_id: str | None = None
    currency: str
    status: str


class POLineOut(BaseModel):
    line_id: str
    item_code: str | None = None
    description: str
    ordered_qty: Decimal
    invoiced_qty: Decimal
    remaining_qty: Decimal
    unit_price: Decimal
    line_total: Decimal


class POOut(BaseModel):
    po_id: str
    vendor_id: str
    vendor_name: str | None = None
    currency: str
    status: str
    issue_date: date
    total_value: Decimal
    remaining_value: Decimal
    lines: list[POLineOut] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    database: str
    extraction_mode: str
    providers_configured: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class RunListFilters(BaseModel):
    decision: Decision | None = None
    vendor: str | None = None
    status: RunStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 50
    offset: int = 0
