from enum import StrEnum


class RunStage(StrEnum):
    UPLOADED = "uploaded"
    RENDERING = "rendering"
    EXTRACTING = "extracting"
    VERIFYING = "verifying"
    VENDOR_RESOLVED = "vendor_resolved"
    PO_CANDIDATES = "po_candidates"
    PO_MATCH = "po_match"
    VALIDATING = "validating"
    DUPLICATE_CHECK = "duplicate_check"
    DECISION = "decision"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW = "review"


class Decision(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class MatchStatus(StrEnum):
    NO_MATCH = "NO_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    MATCHED = "MATCHED"


class POStatus(StrEnum):
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class VendorStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class ConfidenceStatus(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MISSING = "missing"


class UserRole(StrEnum):
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"
    AUDITOR = "auditor"


class ReasonCode(StrEnum):
    ALL_CHECKS_PASSED = "ALL_CHECKS_PASSED"
    MISSING_CRITICAL_FIELD = "MISSING_CRITICAL_FIELD"
    LOW_EXTRACTION_CONFIDENCE = "LOW_EXTRACTION_CONFIDENCE"
    NO_PO_MATCH = "NO_PO_MATCH"
    AMBIGUOUS_PO_MATCH = "AMBIGUOUS_PO_MATCH"
    VENDOR_MISMATCH = "VENDOR_MISMATCH"
    PO_CLOSED = "PO_CLOSED"
    PO_CANCELLED = "PO_CANCELLED"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    AMOUNT_OVER_TOLERANCE = "AMOUNT_OVER_TOLERANCE"
    QUANTITY_EXCEEDED = "QUANTITY_EXCEEDED"
    ARITHMETIC_MISMATCH = "ARITHMETIC_MISMATCH"
    DUPLICATE_EXACT = "DUPLICATE_EXACT"
    DUPLICATE_PROBABLE = "DUPLICATE_PROBABLE"
    DUPLICATE_POSSIBLE = "DUPLICATE_POSSIBLE"
    VENDOR_BLOCKED = "VENDOR_BLOCKED"
    VENDOR_UNRESOLVED = "VENDOR_UNRESOLVED"
    CREDIT_NOTE = "CREDIT_NOTE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    PO_RETRIEVAL_FAILED = "PO_RETRIEVAL_FAILED"
    PO_MATCHING_FAILED = "PO_MATCHING_FAILED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    MANUAL_REVIEW_RESOLVED = "MANUAL_REVIEW_RESOLVED"


class ValidationResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


class StageEventStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
