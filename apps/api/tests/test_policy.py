from decimal import Decimal

from app.domain.enums import Decision, MatchStatus, ReasonCode, ValidationResult
from app.domain.invoice import DuplicateMatch, POMatchResult, ValidationCheck
from app.rules.policy import PolicyEngine


def _match(status: MatchStatus = MatchStatus.MATCHED) -> POMatchResult:
    return POMatchResult(
        status=status,
        selected_po_id="PO-1" if status == MatchStatus.MATCHED else None,
        top_candidate_id="PO-1",
        top_score=0.95 if status == MatchStatus.MATCHED else 0.75,
        runner_up_score=0,
        margin=0.95,
        matched_threshold=0.85,
        possible_threshold=0.70,
        minimum_margin=0.10,
        reason="test",
    )


def test_policy_routes_duplicate_to_review():
    engine = PolicyEngine()
    dups = [DuplicateMatch(match_type="exact", confidence=1.0, evidence="dup")]
    decision, codes, reason = engine.decide(
        [], _match(), dups, {"status": "RESOLVED"}
    )
    assert decision == Decision.REVIEW
    assert ReasonCode.DUPLICATE_EXACT in codes


def test_policy_approves_clean():
    engine = PolicyEngine()
    checks = [ValidationCheck(rule_id="BR-04", name="Currency", result=ValidationResult.PASS, message="ok")]
    decision, codes, reason = engine.decide(
        checks, _match(), [], {"status": "RESOLVED"}
    )
    assert decision == Decision.APPROVE


def test_policy_routes_unknown_vendor_and_no_match_to_review():
    decision, codes, _ = PolicyEngine().decide(
        [], _match(MatchStatus.NO_MATCH), [], {"status": "UNRESOLVED"}
    )
    assert decision == Decision.REVIEW
    assert ReasonCode.VENDOR_UNRESOLVED in codes
    assert ReasonCode.NO_PO_MATCH in codes


def test_policy_rejects_explicit_closed_po():
    checks = [
        ValidationCheck(
            rule_id="BR-03",
            name="PO status",
            result=ValidationResult.FAIL,
            message="PO is closed",
            blocking=True,
        )
    ]
    decision, codes, _ = PolicyEngine().decide(
        checks, _match(), [], {"status": "RESOLVED"}
    )
    assert decision == Decision.REJECT
    assert ReasonCode.PO_CLOSED in codes
