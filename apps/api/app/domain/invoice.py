from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import ConfidenceStatus, Decision, MatchStatus, ReasonCode


class FieldEvidence(BaseModel):
    value: Any = None
    confidence: float = 0.0
    status: ConfidenceStatus = ConfidenceStatus.MISSING
    source_page: int | None = None
    raw_text: str | None = None
    notes: str | None = None


class InvoiceLineExtracted(BaseModel):
    description: FieldEvidence = Field(default_factory=FieldEvidence)
    item_code: FieldEvidence = Field(default_factory=FieldEvidence)
    quantity: FieldEvidence = Field(default_factory=FieldEvidence)
    unit_price: FieldEvidence = Field(default_factory=FieldEvidence)
    tax_rate: FieldEvidence = Field(default_factory=FieldEvidence)
    line_total: FieldEvidence = Field(default_factory=FieldEvidence)


class InvoiceExtracted(BaseModel):
    vendor_name: FieldEvidence = Field(default_factory=FieldEvidence)
    vendor_tax_id: FieldEvidence = Field(default_factory=FieldEvidence)
    invoice_number: FieldEvidence = Field(default_factory=FieldEvidence)
    invoice_date: FieldEvidence = Field(default_factory=FieldEvidence)
    due_date: FieldEvidence = Field(default_factory=FieldEvidence)
    currency: FieldEvidence = Field(default_factory=FieldEvidence)
    subtotal: FieldEvidence = Field(default_factory=FieldEvidence)
    tax: FieldEvidence = Field(default_factory=FieldEvidence)
    total: FieldEvidence = Field(default_factory=FieldEvidence)
    po_reference: FieldEvidence = Field(default_factory=FieldEvidence)
    payment_details: FieldEvidence = Field(default_factory=FieldEvidence)
    lines: list[InvoiceLineExtracted] = Field(default_factory=list)
    extraction_notes: str | None = None


class NormalizedInvoiceLine(BaseModel):
    description: str | None = None
    item_code: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None
    line_total: Decimal | None = None


class NormalizedInvoice(BaseModel):
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str = "USD"
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    po_reference: str | None = None
    payment_details: str | None = None
    lines: list[NormalizedInvoiceLine] = Field(default_factory=list)
    is_credit_note: bool = False


class SignalScore(BaseModel):
    signal: str
    weight: float
    score: float | None
    weighted_score: float
    evidence: str


class POCandidateScore(BaseModel):
    po_id: str
    total_score: float
    signals: list[SignalScore]
    hard_constraints_pass: bool
    hard_constraint_failures: list[str] = Field(default_factory=list)


class POMatchResult(BaseModel):
    status: MatchStatus
    selected_po_id: str | None = None
    top_candidate_id: str | None = None
    top_score: float = 0.0
    runner_up_score: float = 0.0
    margin: float = 0.0
    matched_threshold: float
    possible_threshold: float
    minimum_margin: float
    reason: str


class ValidationCheck(BaseModel):
    rule_id: str
    name: str
    result: str
    message: str
    invoice_value: str | None = None
    po_value: str | None = None
    blocking: bool = False


class DuplicateMatch(BaseModel):
    match_type: str
    matched_run_id: str | None = None
    matched_invoice_id: str | None = None
    confidence: float
    evidence: str


class DecisionResult(BaseModel):
    decision: Decision
    reason_codes: list[ReasonCode]
    human_reason: str
    automated_decision: Decision | None = None
    selected_po_id: str | None = None
    candidate_scores: list[POCandidateScore] = Field(default_factory=list)
    validation_checks: list[ValidationCheck] = Field(default_factory=list)
    duplicate_matches: list[DuplicateMatch] = Field(default_factory=list)


class RunEventPayload(BaseModel):
    stage: str
    status: str
    message: str
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
