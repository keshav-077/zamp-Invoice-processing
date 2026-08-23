from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    tax_id: Mapped[str | None] = mapped_column(String(50), index=True)
    email_domain: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="active")

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(String(50), ForeignKey("vendors.vendor_id"), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remaining_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reference_text: Mapped[str | None] = mapped_column(String(255))

    vendor: Mapped["Vendor"] = relationship(back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    line_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    po_id: Mapped[str] = mapped_column(String(50), ForeignKey("purchase_orders.po_id"), index=True)
    item_code: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_description: Mapped[str] = mapped_column(String(500), nullable=False)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    invoiced_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    vendor_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("vendors.vendor_id"), index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    normalized_invoice_number: Mapped[str | None] = mapped_column(String(100), index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    po_reference: Mapped[str | None] = mapped_column(String(100))
    matched_po_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("purchase_orders.po_id"))
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    decision: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    line_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoices.invoice_id"), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    item_code: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    current_stage: Mapped[str | None] = mapped_column(String(50))
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    decision: Mapped[str | None] = mapped_column(String(20), index=True)
    automated_decision: Mapped[str | None] = mapped_column(String(20))
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    human_reason: Mapped[str | None] = mapped_column(Text)
    vendor_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("vendors.vendor_id"))
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    matched_po_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("purchase_orders.po_id"))
    extraction_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    normalized_invoice: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    vendor_resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    model_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)

    events: Mapped[list["RunEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan", order_by="RunEvent.sequence")
    po_candidates: Mapped[list["POCandidateRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    validation_results: Mapped[list["ValidationResultRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    duplicate_matches: Mapped[list["DuplicateMatchRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    decision_audits: Mapped[list["DecisionAudit"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RunEvent(Base):
    __tablename__ = "run_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["ProcessingRun"] = relationship(back_populates="events")


class POCandidateRecord(Base):
    __tablename__ = "po_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    po_id: Mapped[str] = mapped_column(String(50), ForeignKey("purchase_orders.po_id"))
    total_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    hard_constraints_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    hard_constraint_failures: Mapped[list[str]] = mapped_column(JSON, default=list)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)

    run: Mapped["ProcessingRun"] = relationship(back_populates="po_candidates")


class ValidationResultRecord(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_value: Mapped[str | None] = mapped_column(String(255))
    po_value: Mapped[str | None] = mapped_column(String(255))
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)

    run: Mapped["ProcessingRun"] = relationship(back_populates="validation_results")


class DuplicateMatchRecord(Base):
    __tablename__ = "duplicate_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    match_type: Mapped[str] = mapped_column(String(50), nullable=False)
    matched_run_id: Mapped[str | None] = mapped_column(String(36))
    matched_invoice_id: Mapped[str | None] = mapped_column(String(36))
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped["ProcessingRun"] = relationship(back_populates="duplicate_matches")


class DecisionAudit(Base):
    __tablename__ = "decision_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_runs.run_id"), index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["ProcessingRun"] = relationship(back_populates="decision_audits")
