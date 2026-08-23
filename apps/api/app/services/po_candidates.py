from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PurchaseOrder
from app.domain.enums import POStatus
from app.domain.invoice import NormalizedInvoice
from app.utils.normalize import normalize_po_reference, normalize_text


class POCandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all_pos_with_lines(self) -> list[PurchaseOrder]:
        result = await self.session.execute(
            select(PurchaseOrder).options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.vendor))
        )
        return list(result.scalars().all())

    async def generate_candidates(
        self,
        invoice: NormalizedInvoice,
        vendor_id: str | None,
        max_candidates: int = 5,
    ) -> list[PurchaseOrder]:
        all_pos = await self.get_all_pos_with_lines()
        candidates: list[tuple[float, PurchaseOrder]] = []

        po_ref = normalize_po_reference(invoice.po_reference) if invoice.po_reference else None
        raw_po_ref = (invoice.po_reference or "").upper().replace(" ", "")

        for po in all_pos:
            score = 0.0
            po_norm = normalize_po_reference(po.po_id)
            reference_match = bool(
                po_ref
                and (
                    po_ref == po_norm
                    or raw_po_ref.endswith(po.po_id.upper())
                )
            )

            if reference_match:
                score += 100
            elif po_ref:
                # Keep a small comparison pool, but never let a mismatched explicit
                # reference become an identity match.
                score += 0

            if not reference_match and vendor_id and po.vendor_id != vendor_id:
                continue
            if not po_ref and po.status in (POStatus.CLOSED, POStatus.CANCELLED):
                continue

            if vendor_id and po.vendor_id == vendor_id:
                score += 50
            if invoice.currency and po.currency == invoice.currency:
                score += 10
            if invoice.total is not None and po.total_value is not None:
                invoice_total = abs(float(invoice.total))
                ordered_total = max(float(po.total_value), 0.0)
                if invoice_total or ordered_total:
                    compatibility = min(invoice_total, ordered_total) / max(
                        invoice_total, ordered_total, 1
                    )
                    score += compatibility * 30
            if invoice.lines and po.lines:
                inv_codes = {normalize_text(l.item_code) for l in invoice.lines if l.item_code}
                po_codes = {normalize_text(l.item_code) for l in po.lines if l.item_code}
                overlap = len(inv_codes & po_codes)
                if overlap:
                    score += overlap * 20
                elif any(line.description for line in invoice.lines):
                    descriptions = " ".join(
                        normalize_text(line.description)
                        for line in invoice.lines
                        if line.description
                    )
                    if descriptions and any(
                        normalize_text(po_line.description) in descriptions
                        for po_line in po.lines
                    ):
                        score += 10
            if score > 0:
                candidates.append((score, po))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if not candidates and vendor_id:
            for po in all_pos:
                if po.vendor_id == vendor_id and po.status in (
                    POStatus.OPEN,
                    POStatus.PARTIAL,
                ):
                    candidates.append((10.0, po))

        seen = set()
        result = []
        for _, po in candidates:
            if po.po_id not in seen:
                seen.add(po.po_id)
                result.append(po)
            if len(result) >= max_candidates:
                break
        return result
