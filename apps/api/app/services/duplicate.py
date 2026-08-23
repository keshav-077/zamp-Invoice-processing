from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, ProcessingRun
from app.domain.invoice import DuplicateMatch, NormalizedInvoice
from app.services.normalizer import normalized_invoice_number


class DuplicateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check(
        self,
        invoice: NormalizedInvoice,
        vendor_id: str | None,
        file_hash: str,
        current_run_id: str,
    ) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        norm_num = normalized_invoice_number(invoice)
        matched_run_ids: set[str] = set()

        if file_hash:
            result = await self.session.execute(
                select(ProcessingRun).where(
                    ProcessingRun.file_hash == file_hash,
                    ProcessingRun.run_id != current_run_id,
                    ProcessingRun.status.in_(("completed", "review")),
                )
            )
            for run in result.scalars().all():
                matched_run_ids.add(run.run_id)
                matches.append(
                    DuplicateMatch(
                        match_type="exact",
                        matched_run_id=run.run_id,
                        confidence=1.0,
                        evidence=f"Identical file content previously processed in run {run.run_id}",
                    )
                )

        if (
            vendor_id
            and norm_num
            and invoice.total is not None
            and invoice.currency
        ):
            result = await self.session.execute(
                select(Invoice).where(
                    Invoice.vendor_id == vendor_id,
                    Invoice.normalized_invoice_number == norm_num,
                    Invoice.total == invoice.total,
                    Invoice.currency == invoice.currency,
                    (Invoice.run_id.is_(None)) | (Invoice.run_id != current_run_id),
                )
            )
            for inv in result.scalars().all():
                if inv.run_id and inv.run_id in matched_run_ids:
                    continue
                if inv.run_id:
                    matched_run_ids.add(inv.run_id)
                matches.append(
                    DuplicateMatch(
                        match_type="probable",
                        matched_invoice_id=inv.invoice_id,
                        matched_run_id=inv.run_id,
                        confidence=0.95,
                        evidence=(
                            f"Same vendor, invoice number, amount, and currency: "
                            f"{invoice.invoice_number} / {invoice.total} {invoice.currency}"
                        ),
                    )
                )

        if vendor_id and invoice.total is not None and invoice.invoice_date:
            result = await self.session.execute(
                select(Invoice).where(
                    Invoice.vendor_id == vendor_id,
                    Invoice.total == invoice.total,
                    Invoice.invoice_date == invoice.invoice_date,
                    (Invoice.run_id.is_(None)) | (Invoice.run_id != current_run_id),
                )
            )
            for inv in result.scalars().all():
                if inv.run_id and inv.run_id in matched_run_ids:
                    continue
                if norm_num and inv.normalized_invoice_number == norm_num:
                    continue
                matches.append(
                    DuplicateMatch(
                        match_type="possible",
                        matched_invoice_id=inv.invoice_id,
                        matched_run_id=inv.run_id,
                        confidence=0.80,
                        evidence=f"Similar invoice: same vendor, date, and amount ({invoice.total})",
                    )
                )

        return matches
