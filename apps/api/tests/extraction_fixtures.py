from typing import Any

from app.domain.enums import ConfidenceStatus
from app.domain.invoice import FieldEvidence, InvoiceExtracted, InvoiceLineExtracted


def field(value: Any, confidence: float = 0.95) -> FieldEvidence:
    if value is None:
        return FieldEvidence(
            value=None,
            confidence=0.0,
            status=ConfidenceStatus.MISSING,
        )
    status = (
        ConfidenceStatus.HIGH
        if confidence >= 0.85
        else ConfidenceStatus.MEDIUM
        if confidence >= 0.6
        else ConfidenceStatus.LOW
    )
    return FieldEvidence(
        value=value,
        confidence=confidence,
        status=status,
        source_page=1,
        raw_text=str(value),
    )


def extraction(
    *,
    vendor_name: str | None = "Acme Office Supplies Inc.",
    vendor_tax_id: str | None = "TAX-ACME-001",
    invoice_number: str | None = "INV-2026-001",
    invoice_date: str | None = "2026-01-15",
    currency: str | None = "USD",
    subtotal: str | None = "4500.00",
    tax: str | None = "360.00",
    total: str | None = "4860.00",
    po_reference: str | None = "PO-1001",
    line_description: str | None = "Office chairs ergonomic",
    item_code: str | None = "CHR-001",
    quantity: str | None = "10",
    unit_price: str | None = "450.00",
    line_total: str | None = "4500.00",
    confidence: float = 0.95,
) -> InvoiceExtracted:
    lines = []
    if line_description is not None:
        lines.append(
            InvoiceLineExtracted(
                description=field(line_description, confidence),
                item_code=field(item_code, confidence),
                quantity=field(quantity, confidence),
                unit_price=field(unit_price, confidence),
                line_total=field(line_total, confidence),
            )
        )
    return InvoiceExtracted(
        vendor_name=field(vendor_name, confidence),
        vendor_tax_id=field(vendor_tax_id, confidence),
        invoice_number=field(invoice_number, confidence),
        invoice_date=field(invoice_date, confidence),
        currency=field(currency, confidence),
        subtotal=field(subtotal, confidence),
        tax=field(tax, confidence),
        total=field(total, confidence),
        po_reference=field(po_reference, confidence),
        lines=lines,
        extraction_notes="Injected deterministic test fixture",
    )


EXTRACTIONS = {
    "inv-001": extraction(),
    "inv-003": extraction(
        vendor_name="Global Paper Co",
        vendor_tax_id="TAX-GPC-003",
        invoice_number="GPC-5521",
        invoice_date="2026-01-18",
        subtotal="2500.00",
        tax="200.00",
        total="2700.00",
        po_reference=None,
        line_description="Copy paper A4 80gsm",
        item_code="PAP-A4",
        quantity="500",
        unit_price="5.00",
        line_total="2500.00",
    ),
    "inv-006": extraction(),
    "inv-008": extraction(
        vendor_name="ScanQuality Ltd",
        vendor_tax_id="TAX-SQ-008",
        invoice_number="SQ-???",
        invoice_date="2026-01-10",
        subtotal="800.00",
        tax="64.00",
        total="864.00",
        po_reference="PO-1008",
        line_description="Document scanning services",
        item_code="SVC-SCAN",
        quantity="1",
        unit_price="800.00",
        line_total="800.00",
        confidence=0.45,
    ),
    "unknown-vendor": extraction(
        vendor_name="Oconnor, Fuller and Carter",
        vendor_tax_id=None,
        invoice_number="851918",
        invoice_date="2026-02-10",
        subtotal=None,
        tax=None,
        total="68.53",
        po_reference=None,
        line_description="Unrelated consulting service",
        item_code=None,
        quantity="1",
        unit_price="68.53",
        line_total="68.53",
    ),
    "unrelated-closed": extraction(
        vendor_name="Metro Logistics Inc.",
        vendor_tax_id="TAX-ML-009",
        invoice_number="ML-NO-REF",
        invoice_date="2026-02-01",
        subtotal="1500.00",
        tax="0.00",
        total="1500.00",
        po_reference=None,
        line_description="Freight services",
        item_code="LOG-01",
        quantity="1",
        unit_price="1500.00",
        line_total="1500.00",
    ),
    "explicit-closed": extraction(
        vendor_name="Metro Logistics Inc.",
        vendor_tax_id="TAX-ML-009",
        invoice_number="ML-CLOSED",
        invoice_date="2026-02-01",
        subtotal="1500.00",
        tax="0.00",
        total="1500.00",
        po_reference="PO-1010",
        line_description="Freight services",
        item_code="LOG-01",
        quantity="1",
        unit_price="1500.00",
        line_total="1500.00",
    ),
    "split-1": extraction(
        vendor_name="BuildRight Construction",
        vendor_tax_id="TAX-BRC-004",
        invoice_number="SPLIT-1",
        invoice_date="2026-02-01",
        subtotal="5000.00",
        tax="400.00",
        total="5400.00",
        po_reference="PO-1005",
        line_description="Steel beams grade A",
        item_code="STL-A",
        quantity="10",
        unit_price="500.00",
        line_total="5000.00",
    ),
    "split-2": extraction(
        vendor_name="BuildRight Construction",
        vendor_tax_id="TAX-BRC-004",
        invoice_number="SPLIT-2",
        invoice_date="2026-02-02",
        subtotal="5000.00",
        tax="400.00",
        total="5400.00",
        po_reference="PO-1005",
        line_description="Steel beams grade A",
        item_code="STL-A",
        quantity="10",
        unit_price="500.00",
        line_total="5000.00",
    ),
    "split-3": extraction(
        vendor_name="BuildRight Construction",
        vendor_tax_id="TAX-BRC-004",
        invoice_number="SPLIT-3",
        invoice_date="2026-02-03",
        subtotal="5000.00",
        tax="400.00",
        total="5400.00",
        po_reference="PO-1005",
        line_description="Steel beams grade A",
        item_code="STL-A",
        quantity="10",
        unit_price="500.00",
        line_total="5000.00",
    ),
    "overage": extraction(
        vendor_name="BuildRight Construction",
        vendor_tax_id="TAX-BRC-004",
        invoice_number="OVERAGE-1",
        invoice_date="2026-02-10",
        subtotal="20000.00",
        tax="1600.00",
        total="21600.00",
        po_reference="PO-1005",
        line_description="Steel beams grade A",
        item_code="STL-A",
        quantity="40",
        unit_price="500.00",
        line_total="20000.00",
    ),
    "missing-tax": extraction(
        invoice_number="MISSING-TAX",
        subtotal="4500.00",
        tax=None,
        total="4500.00",
        quantity="10",
    ),
}


async def extract_for_test(image_paths: list[str], file_name: str):
    name = file_name.lower()
    for key, extracted in EXTRACTIONS.items():
        if key in name:
            return extracted.model_copy(deep=True), {
                "provider": "fixture",
                "pages_processed": len(image_paths),
            }
    raise RuntimeError(f"No injected extraction fixture for {file_name}")
