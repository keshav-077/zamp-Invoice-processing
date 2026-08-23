from rapidfuzz import fuzz

from app.config import get_settings
from app.db.models import PurchaseOrder
from app.domain.enums import MatchStatus
from app.domain.invoice import (
    NormalizedInvoice,
    POCandidateScore,
    POMatchResult,
    SignalScore,
)
from app.utils.normalize import normalize_po_reference, normalize_text


class POMatcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.weights = {
            "exact_po_number": self.settings.po_weight_reference,
            "vendor_match": self.settings.po_weight_vendor,
            "amount_compatibility": self.settings.po_weight_amount,
            "line_sku_overlap": self.settings.po_weight_line_items,
            "quantity_compatibility": self.settings.po_weight_quantity,
            "reference_date": self.settings.po_weight_date,
            "semantic_similarity": self.settings.po_weight_semantic,
        }

    @staticmethod
    def _descriptions(invoice: NormalizedInvoice, po: PurchaseOrder) -> list[float]:
        scores: list[float] = []
        for invoice_line in invoice.lines:
            if not invoice_line.description:
                continue
            for po_line in po.lines:
                scores.append(
                    fuzz.token_set_ratio(
                        normalize_text(invoice_line.description),
                        normalize_text(po_line.description),
                    )
                    / 100
                )
        return scores

    def score_candidate(
        self,
        invoice: NormalizedInvoice,
        po: PurchaseOrder,
        vendor_id: str | None,
        vendor_confidence: float,
    ) -> POCandidateScore:
        signals: list[SignalScore] = []
        hard_failures: list[str] = []

        po_ref = normalize_po_reference(invoice.po_reference) if invoice.po_reference else ""
        po_id_norm = normalize_po_reference(po.po_id)
        raw_ref = (invoice.po_reference or "").upper().replace(" ", "")

        raw_signals: list[tuple[str, float | None, str]] = []

        if not invoice.po_reference:
            raw_signals.append(("exact_po_number", None, "PO reference unavailable"))
        elif po_ref == po_id_norm or raw_ref.endswith(po.po_id.upper()):
            raw_signals.append(
                (
                    "exact_po_number",
                    1.0,
                    f"Exact PO reference match: {invoice.po_reference} → {po.po_id}",
                )
            )
        else:
            raw_signals.append(
                (
                    "exact_po_number",
                    0.0,
                    f"PO reference '{invoice.po_reference}' does not match {po.po_id}",
                )
            )
            hard_failures.append("explicit_reference_mismatch")

        if vendor_id and po.vendor_id == vendor_id:
            v_score = min(1.0, vendor_confidence)
            v_evidence = f"Vendor match: {po.vendor_id}"
        elif vendor_id and po.vendor_id != vendor_id:
            v_score = 0.0
            v_evidence = f"Vendor mismatch: invoice vendor {vendor_id} vs PO vendor {po.vendor_id}"
            hard_failures.append("vendor_mismatch")
        else:
            v_score = None
            v_evidence = "Vendor unresolved; signal unavailable"
        raw_signals.append(("vendor_match", v_score, v_evidence))

        if invoice.total is not None and po.total_value is not None:
            invoice_total = abs(float(invoice.total))
            ordered_total = max(float(po.total_value), 0.0)
            if invoice_total == 0 and ordered_total == 0:
                a_score = 1.0
            elif invoice_total == 0 or ordered_total == 0:
                a_score = 0.0
            else:
                a_score = min(invoice_total, ordered_total) / max(
                    invoice_total, ordered_total
                )
            a_evidence = (
                f"Invoice {invoice.total} vs PO ordered total {po.total_value} "
                f"(compatibility {a_score:.0%})"
            )
        else:
            a_score = None
            a_evidence = "Amount comparison unavailable"
        raw_signals.append(("amount_compatibility", a_score, a_evidence))

        inv_codes = {normalize_text(l.item_code) for l in invoice.lines if l.item_code}
        po_codes = {normalize_text(l.item_code) for l in po.lines if l.item_code}
        if inv_codes and po_codes:
            overlap = len(inv_codes & po_codes) / max(len(inv_codes), 1)
            sku_evidence = f"SKU overlap: {inv_codes & po_codes}"
        elif invoice.lines and po.lines:
            desc_scores = self._descriptions(invoice, po)
            overlap = max(desc_scores) if desc_scores else 0.0
            sku_evidence = f"Description similarity: {overlap:.0%}"
        else:
            overlap = None
            sku_evidence = "Line-item comparison unavailable"
        raw_signals.append(("line_sku_overlap", overlap, sku_evidence))

        matched_quantities = 0
        valid_quantities = 0
        for invoice_line in invoice.lines:
            if invoice_line.quantity is None or not invoice_line.item_code:
                continue
            po_line = next(
                (
                    line
                    for line in po.lines
                    if normalize_text(line.item_code)
                    == normalize_text(invoice_line.item_code)
                ),
                None,
            )
            if po_line:
                matched_quantities += 1
                if invoice_line.quantity <= po_line.ordered_qty:
                    valid_quantities += 1
        q_score = (
            valid_quantities / matched_quantities if matched_quantities else None
        )
        raw_signals.append(
            (
                "quantity_compatibility",
                q_score,
                "Quantities within ordered PO limits"
                if q_score == 1.0
                else "One or more quantities exceed ordered PO quantity"
                if q_score is not None
                else "Quantity comparison unavailable",
            )
        )

        if invoice.invoice_date and po.issue_date:
            days_after_issue = (invoice.invoice_date - po.issue_date).days
            if 0 <= days_after_issue <= 365:
                date_score = 1.0
            elif 0 <= days_after_issue <= 730:
                date_score = 0.5
            else:
                date_score = 0.0
            date_evidence = (
                f"Invoice date is {days_after_issue} day(s) after PO issue date"
            )
        else:
            date_score = None
            date_evidence = "Date comparison unavailable"
        raw_signals.append(("reference_date", date_score, date_evidence))

        description_scores = self._descriptions(invoice, po)
        sem_score = max(description_scores) if description_scores else None
        raw_signals.append(
            (
                "semantic_similarity",
                sem_score,
                f"Best line-description similarity: {sem_score:.0%}"
                if sem_score is not None
                else "Semantic comparison unavailable",
            )
        )

        available_weight = sum(
            self.weights[name] for name, score, _ in raw_signals if score is not None
        )
        for name, score, evidence in raw_signals:
            normalized_weight = (
                self.weights[name] / available_weight
                if score is not None and available_weight
                else 0.0
            )
            signals.append(
                SignalScore(
                    signal=name,
                    weight=self.weights[name],
                    score=score,
                    weighted_score=(score or 0.0) * normalized_weight,
                    evidence=evidence,
                )
            )

        total = sum(signal.weighted_score for signal in signals)
        return POCandidateScore(
            po_id=po.po_id,
            total_score=round(total, 4),
            signals=signals,
            hard_constraints_pass=len(hard_failures) == 0,
            hard_constraint_failures=hard_failures,
        )

    def rank_candidates(
        self,
        invoice: NormalizedInvoice,
        pos: list[PurchaseOrder],
        vendor_id: str | None,
        vendor_confidence: float,
    ) -> list[POCandidateScore]:
        scores = [self.score_candidate(invoice, po, vendor_id, vendor_confidence) for po in pos]
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def evaluate_match_quality(
        self, scores: list[POCandidateScore]
    ) -> POMatchResult:
        if not scores:
            return POMatchResult(
                status=MatchStatus.NO_MATCH,
                matched_threshold=self.settings.po_match_min_score,
                possible_threshold=self.settings.po_match_possible_score,
                minimum_margin=self.settings.po_match_min_margin,
                reason="No PO candidates were retrieved",
            )
        top = scores[0]
        runner_up = scores[1].total_score if len(scores) > 1 else 0.0
        margin = round(top.total_score - runner_up, 4)

        if (
            top.total_score >= self.settings.po_match_min_score
            and margin >= self.settings.po_match_min_margin
            and top.hard_constraints_pass
        ):
            status = MatchStatus.MATCHED
            selected_po_id = top.po_id
            reason = "Top candidate passed score, margin, and identity constraints"
        elif top.total_score >= self.settings.po_match_possible_score:
            status = MatchStatus.POSSIBLE_MATCH
            selected_po_id = None
            reason = (
                "Top candidates are too close"
                if margin < self.settings.po_match_min_margin
                else "Top candidate failed an identity constraint"
                if not top.hard_constraints_pass
                else "Top candidate is below the confirmed-match threshold"
            )
        else:
            status = MatchStatus.NO_MATCH
            selected_po_id = None
            reason = "No candidate exceeded the possible-match threshold"

        return POMatchResult(
            status=status,
            selected_po_id=selected_po_id,
            top_candidate_id=top.po_id,
            top_score=top.total_score,
            runner_up_score=runner_up,
            margin=margin,
            matched_threshold=self.settings.po_match_min_score,
            possible_threshold=self.settings.po_match_possible_score,
            minimum_margin=self.settings.po_match_min_margin,
            reason=reason,
        )
