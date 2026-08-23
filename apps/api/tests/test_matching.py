from decimal import Decimal

from app.domain.enums import MatchStatus
from app.domain.invoice import NormalizedInvoice, NormalizedInvoiceLine, POCandidateScore
from app.services.po_matching import POMatcher
from app.db.models import PurchaseOrder, PurchaseOrderLine, Vendor
from datetime import date


def test_po_matcher_exact_reference():
    po = PurchaseOrder(
        po_id="PO-1001", vendor_id="V-001", currency="USD", status="open",
        issue_date=date(2026, 1, 1), total_value=Decimal("4860"), remaining_value=Decimal("4860"),
        lines=[PurchaseOrderLine(line_id="1", po_id="PO-1001", item_code="CHR-001", description="chairs", normalized_description="chairs", ordered_qty=Decimal("10"), invoiced_qty=Decimal("0"), remaining_qty=Decimal("10"), unit_price=Decimal("450"), line_total=Decimal("4500"))],
    )
    invoice = NormalizedInvoice(vendor_name="Acme", currency="USD", total=Decimal("4860"), po_reference="PO-1001", lines=[NormalizedInvoiceLine(item_code="CHR-001", quantity=Decimal("10"), unit_price=Decimal("450"), line_total=Decimal("4500"), description="chairs")])
    matcher = POMatcher()
    score = matcher.score_candidate(invoice, po, "V-001", 1.0)
    assert score.total_score >= 0.85
    assert score.hard_constraints_pass


def _candidate(po_id: str, score: float, passes: bool = True) -> POCandidateScore:
    return POCandidateScore(
        po_id=po_id,
        total_score=score,
        signals=[],
        hard_constraints_pass=passes,
    )


def test_weak_candidate_is_not_selected():
    result = POMatcher().evaluate_match_quality([_candidate("PO-WEAK", 0.32)])
    assert result.status == MatchStatus.NO_MATCH
    assert result.selected_po_id is None


def test_close_high_scores_are_possible_match():
    result = POMatcher().evaluate_match_quality(
        [_candidate("PO-1", 0.87), _candidate("PO-2", 0.85)]
    )
    assert result.status == MatchStatus.POSSIBLE_MATCH
    assert result.selected_po_id is None
    assert result.margin == 0.02


def test_unavailable_signals_are_not_scored_as_zero():
    po = PurchaseOrder(
        po_id="PO-1001",
        vendor_id="V-001",
        currency="USD",
        status="closed",
        issue_date=date(2026, 1, 1),
        total_value=Decimal("4860"),
        remaining_value=Decimal("0"),
        lines=[],
    )
    invoice = NormalizedInvoice(po_reference="PO-1001")
    matcher = POMatcher()
    score = matcher.score_candidate(invoice, po, None, 0)

    assert score.total_score == 1.0
    assert score.hard_constraints_pass
    assert all(
        signal.score is None
        for signal in score.signals
        if signal.signal != "exact_po_number"
    )
    result = matcher.evaluate_match_quality([score])
    assert result.status == MatchStatus.MATCHED
    assert result.selected_po_id == "PO-1001"


def test_normalize_invoice_number():
    from app.utils.normalize import normalize_invoice_number
    assert normalize_invoice_number("INV-2026-001") == "inv2026001"
