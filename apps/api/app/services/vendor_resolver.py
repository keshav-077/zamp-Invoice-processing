from rapidfuzz import fuzz

from app.config import get_settings
from app.db.models import Vendor
from app.utils.normalize import normalize_vendor_name


class VendorResolver:
    def __init__(self) -> None:
        self.settings = get_settings()

    def resolve(self, vendor_name: str | None, vendor_tax_id: str | None, vendors: list[Vendor]) -> dict:
        if not vendor_name and not vendor_tax_id:
            return {
                "status": "UNRESOLVED",
                "vendor_id": None,
                "selected_vendor_id": None,
                "confidence": 0.0,
                "method": "none",
                "evidence": "No vendor identifiers on invoice",
                "candidates": [],
            }

        if vendor_tax_id:
            for v in vendors:
                if v.tax_id and v.tax_id.lower() == vendor_tax_id.lower():
                    return {
                        "status": "RESOLVED",
                        "vendor_id": v.vendor_id,
                        "selected_vendor_id": v.vendor_id,
                        "vendor_name": v.legal_name,
                        "vendor_status": v.status,
                        "confidence": 1.0,
                        "method": "tax_id_exact",
                        "evidence": f"Exact tax ID match: {v.tax_id}",
                    }

        norm_name = normalize_vendor_name(vendor_name)
        best_match: Vendor | None = None
        best_score = 0.0
        best_method = "fuzzy_name"
        ranked_candidates: list[dict] = []

        for v in vendors:
            normalized_legal_name = normalize_vendor_name(v.legal_name)
            if normalized_legal_name == norm_name:
                return {
                    "status": "RESOLVED",
                    "vendor_id": v.vendor_id,
                    "selected_vendor_id": v.vendor_id,
                    "vendor_name": v.legal_name,
                    "vendor_status": v.status,
                    "confidence": 1.0,
                    "method": "normalized_name_exact",
                    "evidence": f"Normalized name match: {v.legal_name}",
                }

            score = max(
                fuzz.token_set_ratio(norm_name, normalized_legal_name),
                fuzz.WRatio(norm_name, normalized_legal_name),
            )
            method = "fuzzy_name"
            for alias in v.aliases or []:
                normalized_alias = normalize_vendor_name(alias)
                alias_score = max(
                    fuzz.token_set_ratio(norm_name, normalized_alias),
                    fuzz.WRatio(norm_name, normalized_alias),
                )
                if alias_score > score:
                    score = alias_score
                    method = "alias_fuzzy"

            ranked_candidates.append(
                {
                    "vendor_id": v.vendor_id,
                    "name": v.legal_name,
                    "score": round(score / 100, 4),
                }
            )
            if score > best_score:
                best_score = score
                best_match = v
                best_method = method

        minimum_score = self.settings.vendor_match_min_score * 100
        if best_match and best_score >= minimum_score:
            return {
                "status": "RESOLVED",
                "vendor_id": best_match.vendor_id,
                "selected_vendor_id": best_match.vendor_id,
                "vendor_name": best_match.legal_name,
                "vendor_status": best_match.status,
                "confidence": best_score / 100,
                "method": best_method,
                "evidence": f"Fuzzy match ({best_score}%): invoice '{vendor_name}' → '{best_match.legal_name}'",
                "candidates": sorted(
                    ranked_candidates, key=lambda candidate: candidate["score"], reverse=True
                )[:3],
            }

        return {
            "status": "UNRESOLVED",
            "vendor_id": None,
            "selected_vendor_id": None,
            "confidence": best_score / 100 if best_match else 0.0,
            "method": "unresolved",
            "evidence": f"Could not resolve vendor '{vendor_name}' (best score: {best_score}%)",
            "candidates": sorted(
                ranked_candidates, key=lambda candidate: candidate["score"], reverse=True
            )[:3],
        }
