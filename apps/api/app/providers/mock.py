import json
import re
from typing import Any

from app.domain.enums import ConfidenceStatus
from app.domain.invoice import FieldEvidence, InvoiceExtracted, InvoiceLineExtracted
from app.providers.base import ExtractionProvider


class MockExtractionProvider(ExtractionProvider):
    """Test-only provider; extraction data must be injected by tests."""

    name = "mock"

    async def extract_invoice(self, image_paths: list[str], file_name: str) -> tuple[InvoiceExtracted, dict[str, Any]]:
        raise RuntimeError(
            "Mock extraction contains no production invoice fixtures. "
            "Tests must inject structured extraction data explicitly."
        )

    async def verify_invoice(
        self, extracted: InvoiceExtracted, image_paths: list[str]
    ) -> tuple[InvoiceExtracted, dict[str, Any]]:
        return extracted, {"provider": self.name, "verified": True}


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return json.loads(cleaned)


def _dict_to_extraction(data: dict[str, Any]) -> InvoiceExtracted:
    def fe(d: dict | None) -> FieldEvidence:
        if not d:
            return FieldEvidence()
        conf = float(d.get("confidence", 0.8))
        status = ConfidenceStatus(d.get("status", "high" if conf >= 0.85 else "medium"))
        return FieldEvidence(
            value=d.get("value"),
            confidence=conf,
            status=status,
            source_page=d.get("source_page"),
            raw_text=d.get("raw_text"),
        )

    lines = []
    for ln in data.get("lines", []):
        lines.append(
            InvoiceLineExtracted(
                description=fe(ln.get("description")),
                item_code=fe(ln.get("item_code")),
                quantity=fe(ln.get("quantity")),
                unit_price=fe(ln.get("unit_price")),
                tax_rate=fe(ln.get("tax_rate")),
                line_total=fe(ln.get("line_total")),
            )
        )
    return InvoiceExtracted(
        vendor_name=fe(data.get("vendor_name")),
        vendor_tax_id=fe(data.get("vendor_tax_id")),
        invoice_number=fe(data.get("invoice_number")),
        invoice_date=fe(data.get("invoice_date")),
        due_date=fe(data.get("due_date")),
        currency=fe(data.get("currency")),
        subtotal=fe(data.get("subtotal")),
        tax=fe(data.get("tax")),
        total=fe(data.get("total")),
        po_reference=fe(data.get("po_reference")),
        payment_details=fe(data.get("payment_details")),
        lines=lines,
        extraction_notes=data.get("extraction_notes"),
    )
