from decimal import Decimal

from app.domain.invoice import FieldEvidence, InvoiceExtracted, NormalizedInvoice, NormalizedInvoiceLine
from app.utils.normalize import normalize_invoice_number, normalize_po_reference, parse_date, parse_decimal


def _get_value(field: FieldEvidence) -> str | None:
    if field.value is None:
        return None
    return str(field.value).strip() or None


def normalize_extraction(extracted: InvoiceExtracted) -> NormalizedInvoice:
    total = parse_decimal(_get_value(extracted.total))
    is_credit = total is not None and total < 0
    lines = []
    for ln in extracted.lines:
        lines.append(
            NormalizedInvoiceLine(
                description=_get_value(ln.description),
                item_code=_get_value(ln.item_code),
                quantity=parse_decimal(_get_value(ln.quantity)),
                unit_price=parse_decimal(_get_value(ln.unit_price)),
                tax_rate=parse_decimal(_get_value(ln.tax_rate)),
                line_total=parse_decimal(_get_value(ln.line_total)),
            )
        )
    currency = _get_value(extracted.currency) or "USD"
    return NormalizedInvoice(
        vendor_name=_get_value(extracted.vendor_name),
        vendor_tax_id=_get_value(extracted.vendor_tax_id),
        invoice_number=_get_value(extracted.invoice_number),
        invoice_date=parse_date(_get_value(extracted.invoice_date)),
        due_date=parse_date(_get_value(extracted.due_date)),
        currency=currency.upper()[:3],
        subtotal=parse_decimal(_get_value(extracted.subtotal)),
        tax=parse_decimal(_get_value(extracted.tax)),
        total=total,
        po_reference=normalize_po_reference(_get_value(extracted.po_reference)) or _get_value(extracted.po_reference),
        payment_details=_get_value(extracted.payment_details),
        lines=lines,
        is_credit_note=is_credit,
    )


def get_material_field_confidences(extracted: InvoiceExtracted) -> dict[str, float]:
    return {
        "vendor_name": extracted.vendor_name.confidence,
        "invoice_number": extracted.invoice_number.confidence,
        "invoice_date": extracted.invoice_date.confidence,
        "currency": extracted.currency.confidence,
        "total": extracted.total.confidence,
    }


def needs_verification(extracted: InvoiceExtracted, threshold: float) -> bool:
    material = get_material_field_confidences(extracted)
    return any(v < threshold for v in material.values())


def normalized_invoice_number(invoice: NormalizedInvoice) -> str:
    return normalize_invoice_number(invoice.invoice_number)
