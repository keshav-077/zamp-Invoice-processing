from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Invoice, ProcessingRun, PurchaseOrder
from app.domain.enums import POStatus, ValidationResult, VendorStatus
from app.domain.invoice import NormalizedInvoice, ValidationCheck
from app.services.normalizer import normalized_invoice_number


class ValidationEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def validate(
        self,
        invoice: NormalizedInvoice,
        po: PurchaseOrder | None,
        vendor_id: str | None,
        vendor_resolution: dict,
        extracted_confidences: dict[str, float],
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        threshold = self.settings.extraction_confidence_threshold

        for field, conf in extracted_confidences.items():
            blocking = field in ("vendor_name", "invoice_number", "total", "currency")
            below = conf < threshold
            checks.append(
                ValidationCheck(
                    rule_id=f"CONF_{field.upper()}",
                    name=f"Extraction confidence: {field}",
                    result=ValidationResult.FAIL if below and blocking else ValidationResult.WARN if below else ValidationResult.PASS,
                    message=f"Confidence {conf:.0%}" + (" below threshold" if below else ""),
                    invoice_value=f"{conf:.0%}",
                    blocking=blocking and below,
                )
            )

        if invoice.total is None:
            checks.append(ValidationCheck(rule_id="BR-01", name="Invoice total present", result=ValidationResult.FAIL, message="Missing invoice total", blocking=True))
        if not invoice.currency:
            checks.append(ValidationCheck(rule_id="BR-01", name="Currency present", result=ValidationResult.FAIL, message="Missing currency", blocking=True))
        if not invoice.vendor_name and not vendor_id:
            checks.append(ValidationCheck(rule_id="BR-01", name="Vendor identity", result=ValidationResult.FAIL, message="Missing vendor identity", blocking=True))
        if not invoice.invoice_number:
            checks.append(ValidationCheck(rule_id="BR-01", name="Invoice number present", result=ValidationResult.FAIL, message="Missing invoice number", blocking=True))
        if not invoice.invoice_date:
            checks.append(ValidationCheck(rule_id="BR-01", name="Invoice date present", result=ValidationResult.FAIL, message="Missing invoice date", blocking=True))
        if vendor_resolution.get("vendor_status") == VendorStatus.BLOCKED:
            checks.append(
                ValidationCheck(
                    rule_id="BR-13",
                    name="Vendor status",
                    result=ValidationResult.FAIL,
                    message="Resolved vendor is blocked",
                    po_value=VendorStatus.BLOCKED.value,
                    blocking=True,
                )
            )

        if invoice.is_credit_note:
            checks.append(ValidationCheck(rule_id="BR-12", name="Credit note policy", result=ValidationResult.WARN, message="Credit note requires separate review policy", blocking=True))

        if invoice.subtotal is not None and invoice.tax is not None and invoice.total is not None:
            calc = invoice.subtotal + invoice.tax
            diff = abs(calc - invoice.total)
            ok = diff <= Decimal(str(self.settings.rounding_tolerance))
            checks.append(
                ValidationCheck(
                    rule_id="BR-11",
                    name="Arithmetic: subtotal + tax = total",
                    result=ValidationResult.PASS if ok else ValidationResult.FAIL,
                    message=f"Calculated {calc}, stated {invoice.total}, diff {diff}",
                    invoice_value=str(invoice.total),
                    po_value=str(calc),
                    blocking=not ok,
                )
            )

        for i, line in enumerate(invoice.lines):
            if (
                line.quantity is not None
                and line.unit_price is not None
                and line.line_total is not None
            ):
                calc_line = line.quantity * line.unit_price
                diff = abs(calc_line - line.line_total)
                ok = diff <= Decimal(str(self.settings.rounding_tolerance))
                checks.append(
                    ValidationCheck(
                        rule_id="BR-11",
                        name=f"Line {i+1} extension",
                        result=ValidationResult.PASS if ok else ValidationResult.FAIL,
                        message=f"Qty×Price={calc_line}, line total={line.line_total}",
                        blocking=not ok,
                    )
                )

        if not po:
            checks.append(
                ValidationCheck(
                    rule_id="NO_PO",
                    name="PO validation",
                    result=ValidationResult.SKIP,
                    message="PO-specific validation skipped because no PO was confidently matched",
                    blocking=False,
                )
            )
            return checks

        if vendor_id and po.vendor_id != vendor_id:
            checks.append(ValidationCheck(rule_id="BR-02", name="Vendor match", result=ValidationResult.FAIL, message=f"Invoice vendor {vendor_id} ≠ PO vendor {po.vendor_id}", invoice_value=vendor_id, po_value=po.vendor_id, blocking=True))

        if po.status == POStatus.CLOSED:
            checks.append(ValidationCheck(rule_id="BR-03", name="PO status", result=ValidationResult.FAIL, message="PO is closed", po_value=po.status, blocking=True))
        elif po.status == POStatus.CANCELLED:
            checks.append(ValidationCheck(rule_id="BR-03", name="PO status", result=ValidationResult.FAIL, message="PO is cancelled", po_value=po.status, blocking=True))
        else:
            checks.append(ValidationCheck(rule_id="BR-03", name="PO status", result=ValidationResult.PASS, message=f"PO status: {po.status}", po_value=po.status))

        if invoice.currency != po.currency:
            checks.append(ValidationCheck(rule_id="BR-04", name="Currency match", result=ValidationResult.FAIL, message="Currency mismatch", invoice_value=invoice.currency, po_value=po.currency, blocking=True))
        else:
            checks.append(ValidationCheck(rule_id="BR-04", name="Currency match", result=ValidationResult.PASS, message="Currencies match", invoice_value=invoice.currency, po_value=po.currency))

        if invoice.total is not None and po.remaining_value is not None:
            abs_tol = Decimal(str(self.settings.amount_tolerance_absolute))
            pct_tol = po.remaining_value * Decimal(
                str(self.settings.amount_tolerance_percent / 100)
            )
            allowed_overage = max(abs_tol, pct_tol)
            maximum_allowed = po.remaining_value + allowed_overage
            within = invoice.total <= maximum_allowed
            checks.append(
                ValidationCheck(
                    rule_id="BR-05",
                    name="Remaining PO balance",
                    result=ValidationResult.PASS if within else ValidationResult.FAIL,
                    message=(
                        f"Invoice {invoice.total} is within remaining balance "
                        f"{po.remaining_value} plus tolerance {allowed_overage}"
                        if within
                        else f"Invoice {invoice.total} exceeds maximum allowed {maximum_allowed}"
                    ),
                    invoice_value=str(invoice.total),
                    po_value=str(po.remaining_value),
                    blocking=not within,
                )
            )

        for il in invoice.lines:
            if not il.item_code or not il.quantity:
                continue
            po_line = next((pl for pl in po.lines if pl.item_code and il.item_code and pl.item_code.lower() == il.item_code.lower()), None)
            if po_line and il.quantity > po_line.remaining_qty:
                checks.append(
                    ValidationCheck(
                        rule_id="BR-06",
                        name=f"Quantity: {il.item_code}",
                        result=ValidationResult.FAIL,
                        message=f"Invoiced {il.quantity} > remaining {po_line.remaining_qty}",
                        invoice_value=str(il.quantity),
                        po_value=str(po_line.remaining_qty),
                        blocking=True,
                    )
                )

        return checks
