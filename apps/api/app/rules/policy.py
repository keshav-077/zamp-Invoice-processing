from app.config import get_settings
from app.domain.enums import Decision, MatchStatus, ReasonCode, ValidationResult
from app.domain.invoice import DuplicateMatch, POMatchResult, ValidationCheck


class PolicyEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _configured_decision(value: str, default: Decision) -> Decision:
        try:
            return Decision(value.upper())
        except ValueError:
            return default

    def decide(
        self,
        checks: list[ValidationCheck],
        match_result: POMatchResult,
        duplicates: list[DuplicateMatch],
        vendor_resolution: dict,
        is_credit_note: bool = False,
    ) -> tuple[Decision, list[ReasonCode], str]:
        reason_codes: list[ReasonCode] = []
        blocking_failures = [c for c in checks if c.blocking and c.result == ValidationResult.FAIL]

        if duplicates:
            duplicate_types = {duplicate.match_type for duplicate in duplicates}
            if "exact" in duplicate_types:
                reason_codes.append(ReasonCode.DUPLICATE_EXACT)
            if "probable" in duplicate_types:
                reason_codes.append(ReasonCode.DUPLICATE_PROBABLE)
            if "possible" in duplicate_types:
                reason_codes.append(ReasonCode.DUPLICATE_POSSIBLE)

        if is_credit_note:
            reason_codes.append(ReasonCode.CREDIT_NOTE)

        if vendor_resolution.get("status") != "RESOLVED":
            reason_codes.append(ReasonCode.VENDOR_UNRESOLVED)

        if match_result.status == MatchStatus.NO_MATCH:
            reason_codes.append(ReasonCode.NO_PO_MATCH)
        elif match_result.status == MatchStatus.POSSIBLE_MATCH:
            reason_codes.append(ReasonCode.AMBIGUOUS_PO_MATCH)

        for check in blocking_failures:
            if check.rule_id == "BR-02":
                reason_codes.append(ReasonCode.VENDOR_MISMATCH)
            elif check.rule_id == "BR-03" and "closed" in check.message.lower():
                reason_codes.append(ReasonCode.PO_CLOSED)
            elif check.rule_id == "BR-03" and "cancelled" in check.message.lower():
                reason_codes.append(ReasonCode.PO_CANCELLED)
            elif check.rule_id == "BR-04":
                reason_codes.append(ReasonCode.CURRENCY_MISMATCH)
            elif check.rule_id == "BR-05":
                reason_codes.append(ReasonCode.AMOUNT_OVER_TOLERANCE)
            elif check.rule_id == "BR-06":
                reason_codes.append(ReasonCode.QUANTITY_EXCEEDED)
            elif check.rule_id == "BR-11":
                reason_codes.append(ReasonCode.ARITHMETIC_MISMATCH)
            elif check.rule_id == "BR-13":
                reason_codes.append(ReasonCode.VENDOR_BLOCKED)
            elif check.rule_id.startswith("CONF_"):
                reason_codes.append(ReasonCode.LOW_EXTRACTION_CONFIDENCE)
            elif check.rule_id == "BR-01":
                reason_codes.append(ReasonCode.MISSING_CRITICAL_FIELD)

        reason_codes = list(dict.fromkeys(reason_codes))

        if ReasonCode.VENDOR_BLOCKED in reason_codes:
            return Decision.REJECT, reason_codes, "Resolved vendor is blocked by policy."
        if duplicates:
            decision = self._configured_decision(
                self.settings.duplicate_decision, Decision.REVIEW
            )
            return (
                decision,
                reason_codes,
                "Potential duplicate invoice detected — automatic approval blocked.",
            )
        if ReasonCode.ARITHMETIC_MISMATCH in reason_codes:
            return Decision.REJECT, reason_codes, "Invoice arithmetic does not reconcile."
        if ReasonCode.PO_CANCELLED in reason_codes:
            decision = self._configured_decision(
                self.settings.po_cancelled_decision, Decision.REJECT
            )
            return decision, reason_codes, "Matched PO is cancelled."
        if ReasonCode.PO_CLOSED in reason_codes:
            decision = self._configured_decision(
                self.settings.po_closed_decision, Decision.REJECT
            )
            return decision, reason_codes, "Matched PO is closed."
        if ReasonCode.CURRENCY_MISMATCH in reason_codes:
            decision = self._configured_decision(
                self.settings.currency_mismatch_decision, Decision.REJECT
            )
            return decision, reason_codes, "Invoice currency differs from the matched PO."
        if ReasonCode.AMOUNT_OVER_TOLERANCE in reason_codes:
            decision = self._configured_decision(
                self.settings.amount_over_tolerance_decision, Decision.REVIEW
            )
            return decision, reason_codes, "Invoice exceeds the matched PO's remaining balance."

        if ReasonCode.VENDOR_UNRESOLVED in reason_codes:
            return (
                Decision.REVIEW,
                reason_codes,
                "Vendor was not found in the approved vendor list.",
            )
        if match_result.status == MatchStatus.NO_MATCH:
            return (
                Decision.REVIEW,
                reason_codes,
                "No PO candidate exceeded the possible-match threshold.",
            )
        if match_result.status == MatchStatus.POSSIBLE_MATCH:
            return (
                Decision.REVIEW,
                reason_codes,
                "PO match is plausible but not confident enough for automatic selection.",
            )
        if is_credit_note:
            return Decision.REVIEW, reason_codes, "Credit note requires manual review per policy."
        if blocking_failures:
            return Decision.REVIEW, reason_codes, "One or more validation checks require human review."

        reason_codes.append(ReasonCode.ALL_CHECKS_PASSED)
        return Decision.APPROVE, reason_codes, "All validation checks passed. Invoice matches PO within tolerance. Safe for straight-through processing."
