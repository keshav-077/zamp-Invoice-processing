import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.models import (
    DecisionAudit,
    DuplicateMatchRecord,
    Invoice,
    InvoiceLine,
    POCandidateRecord,
    ProcessingRun,
    PurchaseOrder,
    RunEvent,
    ValidationResultRecord,
    Vendor,
)
from app.domain.enums import (
    Decision,
    MatchStatus,
    ReasonCode,
    RunStage,
    RunStatus,
    StageEventStatus,
)
from app.providers.factory import (
    ExtractionProvidersError,
    extract_with_fallback,
    get_extraction_providers,
)
from app.rules.policy import PolicyEngine
from app.rules.validation import ValidationEngine
from app.services.documents import DocumentProcessor, is_pdf
from app.services.duplicate import DuplicateService
from app.services.normalizer import get_material_field_confidences, needs_verification, normalize_extraction, normalized_invoice_number
from app.services.po_candidates import POCandidateService
from app.services.po_matching import POMatcher
from app.services.vendor_resolver import VendorResolver
from app.utils.normalize import normalize_text


class WorkflowOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.doc_processor = DocumentProcessor()
        self.vendor_resolver = VendorResolver()
        self.po_candidate_service = POCandidateService(session)
        self.po_matcher = POMatcher()
        self.validation_engine = ValidationEngine()
        self.policy_engine = PolicyEngine()
        self.duplicate_service = DuplicateService(session)
        self._sequence = 0

    async def _emit(self, run: ProcessingRun, stage: str, status: str, message: str, data: dict | None = None) -> None:
        self._sequence += 1
        event = RunEvent(
            run_id=run.run_id,
            sequence=self._sequence,
            stage=stage,
            status=status,
            message=message,
            data=data,
        )
        self.session.add(event)
        run.current_stage = stage
        await self.session.flush()

    async def _complete_review(
        self,
        run: ProcessingRun,
        start: datetime,
        reason_codes: list[ReasonCode],
        message: str,
    ) -> None:
        run.decision = Decision.REVIEW.value
        run.automated_decision = Decision.REVIEW.value
        run.reason_codes = [reason.value for reason in reason_codes]
        run.human_reason = message
        run.status = RunStatus.REVIEW.value
        run.current_stage = RunStage.COMPLETED.value
        run.completed_at = datetime.now(timezone.utc)
        run.processing_time_ms = int(
            (run.completed_at - start).total_seconds() * 1000
        )
        await self._emit(
            run,
            RunStage.DECISION,
            StageEventStatus.WARNING,
            "Decision: REVIEW",
            {"decision": Decision.REVIEW.value, "reasons": run.reason_codes},
        )
        await self._emit(
            run, RunStage.COMPLETED, StageEventStatus.WARNING, message
        )

    async def process_run(self, run_id: str) -> None:
        start = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ProcessingRun).where(ProcessingRun.run_id == run_id)
        )
        run = result.scalar_one()
        run.status = RunStatus.RUNNING.value
        await self.session.flush()

        try:
            await self._emit(run, RunStage.UPLOADED, StageEventStatus.SUCCESS, f"Invoice uploaded: {run.file_name}")

            file_name = run.file_name or "invoice.pdf"
            if is_pdf(file_name):
                await self._emit(run, RunStage.RENDERING, StageEventStatus.RUNNING, "Rendering PDF pages for analysis...")
            else:
                await self._emit(run, RunStage.RENDERING, StageEventStatus.RUNNING, "Preparing image for analysis...")
            image_paths = self.doc_processor.prepare_images(run.run_id, run.file_path)
            page_label = "page" if len(image_paths) == 1 else "pages"
            await self._emit(
                run,
                RunStage.RENDERING,
                StageEventStatus.SUCCESS,
                f"Prepared {len(image_paths)} {page_label}",
                {"pages": len(image_paths)},
            )

            await self._emit(run, RunStage.EXTRACTING, StageEventStatus.RUNNING, "Extracting invoice fields via multimodal model...")
            extracted, model_meta = await extract_with_fallback(image_paths, file_name)
            run.extraction_data = extracted.model_dump()
            run.model_metadata = model_meta
            await self._emit(run, RunStage.EXTRACTING, StageEventStatus.SUCCESS, "Extraction complete", {"provider": model_meta.get("provider")})

            if needs_verification(extracted, self.settings.extraction_confidence_threshold):
                providers = get_extraction_providers()
                successful_provider = next(
                    (
                        provider
                        for provider in providers
                        if provider.name == model_meta.get("provider")
                    ),
                    None,
                )
                if successful_provider and successful_provider.supports_verification:
                    await self._emit(run, RunStage.VERIFYING, StageEventStatus.RUNNING, "Verifying uncertain fields...")
                    extracted, verify_meta = await successful_provider.verify_invoice(extracted, image_paths)
                    run.extraction_data = extracted.model_dump()
                    run.model_metadata = {**(run.model_metadata or {}), "verification": verify_meta}
                    await self._emit(run, RunStage.VERIFYING, StageEventStatus.SUCCESS, "Verification complete")
                else:
                    run.model_metadata = {
                        **(run.model_metadata or {}),
                        "verification": {
                            "performed": False,
                            "reason": "Provider does not implement verification",
                        },
                    }

            normalized = normalize_extraction(extracted)
            run.normalized_invoice = normalized.model_dump(mode="json")
            run.vendor_name = normalized.vendor_name
            run.invoice_number = normalized.invoice_number
            run.total = normalized.total
            run.currency = normalized.currency

            vendors_result = await self.session.execute(select(Vendor))
            vendors = list(vendors_result.scalars().all())

            await self._emit(run, RunStage.VENDOR_RESOLVED, StageEventStatus.RUNNING, "Resolving vendor...")
            resolution = self.vendor_resolver.resolve(normalized.vendor_name, normalized.vendor_tax_id, vendors)
            run.vendor_resolution = resolution
            if resolution.get("vendor_id"):
                run.vendor_id = resolution["vendor_id"]
            await self._emit(run, RunStage.VENDOR_RESOLVED, StageEventStatus.SUCCESS, resolution.get("evidence", "Vendor resolved"), resolution)

            await self._emit(run, RunStage.PO_CANDIDATES, StageEventStatus.RUNNING, "Retrieving PO candidates...")
            try:
                candidates = await self.po_candidate_service.generate_candidates(
                    normalized, resolution.get("vendor_id")
                )
            except Exception as error:
                run.error_message = str(error)
                await self._complete_review(
                    run,
                    start,
                    [ReasonCode.PO_RETRIEVAL_FAILED],
                    "PO candidate retrieval failed — routed to human review.",
                )
                return
            await self._emit(run, RunStage.PO_CANDIDATES, StageEventStatus.SUCCESS, f"Found {len(candidates)} candidate(s)", {"count": len(candidates)})

            await self._emit(run, RunStage.PO_MATCH, StageEventStatus.RUNNING, "Scoring PO candidates...")
            try:
                scores = self.po_matcher.rank_candidates(
                    normalized,
                    candidates,
                    resolution.get("vendor_id"),
                    resolution.get("confidence", 0),
                )
                match_result = self.po_matcher.evaluate_match_quality(scores)
            except Exception as error:
                run.error_message = str(error)
                await self._complete_review(
                    run,
                    start,
                    [ReasonCode.PO_MATCHING_FAILED],
                    "PO matching failed — routed to human review.",
                )
                return

            for rank, score in enumerate(scores):
                self.session.add(
                    POCandidateRecord(
                        run_id=run.run_id,
                        po_id=score.po_id,
                        total_score=Decimal(str(score.total_score)),
                        rank=rank + 1,
                        signals=[s.model_dump() for s in score.signals],
                        hard_constraints_pass=score.hard_constraints_pass,
                        hard_constraint_failures=score.hard_constraint_failures,
                        selected=score.po_id == match_result.selected_po_id,
                    )
                )

            selected_po: PurchaseOrder | None = None
            if (
                match_result.status == MatchStatus.MATCHED
                and match_result.selected_po_id
            ):
                po_result = await self.session.execute(
                    select(PurchaseOrder)
                    .options(selectinload(PurchaseOrder.lines))
                    .where(PurchaseOrder.po_id == match_result.selected_po_id)
                )
                selected_po = po_result.scalar_one_or_none()
                run.matched_po_id = match_result.selected_po_id
            else:
                run.matched_po_id = None

            await self._emit(
                run,
                RunStage.PO_MATCH,
                StageEventStatus.SUCCESS
                if match_result.status == MatchStatus.MATCHED
                else StageEventStatus.WARNING,
                (
                    f"Matched PO: {match_result.selected_po_id} "
                    f"(score {match_result.top_score:.3f})"
                    if match_result.status == MatchStatus.MATCHED
                    else f"{match_result.status.value}: top candidate "
                    f"{match_result.top_candidate_id or 'none'} "
                    f"(score {match_result.top_score:.3f}); no PO selected"
                ),
                match_result.model_dump(mode="json"),
            )

            await self._emit(run, RunStage.VALIDATING, StageEventStatus.RUNNING, "Running deterministic validation...")
            confidences = get_material_field_confidences(extracted)
            checks = self.validation_engine.validate(normalized, selected_po, resolution.get("vendor_id"), resolution, confidences)
            for check in checks:
                self.session.add(
                    ValidationResultRecord(
                        run_id=run.run_id,
                        rule_id=check.rule_id,
                        name=check.name,
                        result=check.result,
                        message=check.message,
                        invoice_value=check.invoice_value,
                        po_value=check.po_value,
                        blocking=check.blocking,
                    )
                )
            failed = [c for c in checks if c.result == "fail"]
            await self._emit(run, RunStage.VALIDATING, StageEventStatus.SUCCESS if not failed else StageEventStatus.WARNING, f"{len(checks)} checks run, {len(failed)} failed")

            await self._emit(run, RunStage.DUPLICATE_CHECK, StageEventStatus.RUNNING, "Checking for duplicates...")
            duplicates = await self.duplicate_service.check(normalized, resolution.get("vendor_id"), run.file_hash or "", run.run_id)
            for dup in duplicates:
                self.session.add(
                    DuplicateMatchRecord(
                        run_id=run.run_id,
                        match_type=dup.match_type,
                        matched_run_id=dup.matched_run_id,
                        matched_invoice_id=dup.matched_invoice_id,
                        confidence=Decimal(str(dup.confidence)),
                        evidence=dup.evidence,
                    )
                )
            await self._emit(run, RunStage.DUPLICATE_CHECK, StageEventStatus.SUCCESS if not duplicates else StageEventStatus.WARNING, f"{len(duplicates)} duplicate match(es) found")

            await self._emit(run, RunStage.DECISION, StageEventStatus.RUNNING, "Applying decision policy...")
            decision, reason_codes, human_reason = self.policy_engine.decide(
                checks,
                match_result,
                duplicates,
                resolution,
                normalized.is_credit_note,
            )
            run.decision = decision.value
            run.automated_decision = decision.value
            run.reason_codes = [rc.value for rc in reason_codes]
            run.human_reason = human_reason
            run.status = RunStatus.COMPLETED.value if decision != Decision.REVIEW else RunStatus.REVIEW.value
            run.current_stage = RunStage.COMPLETED.value
            run.completed_at = datetime.now(timezone.utc)
            run.processing_time_ms = int((run.completed_at - start).total_seconds() * 1000)

            await self._emit(run, RunStage.DECISION, StageEventStatus.SUCCESS, f"Decision: {decision.value}", {"decision": decision.value, "reasons": run.reason_codes})
            await self._emit(run, RunStage.COMPLETED, StageEventStatus.SUCCESS, human_reason)

            if (
                decision == Decision.APPROVE
                and selected_po
                and match_result.status == MatchStatus.MATCHED
            ):
                await self._consume_po_balance(selected_po, normalized)
            await self._persist_invoice(
                run,
                normalized,
                resolution.get("vendor_id"),
                selected_po.po_id if selected_po else None,
                decision.value,
            )

        except ExtractionProvidersError as e:
            run.error_message = str(e)
            await self._complete_review(
                run,
                start,
                [ReasonCode.EXTRACTION_FAILED, ReasonCode.EXTERNAL_SERVICE_ERROR],
                "Invoice extraction failed — routed to human review without manufactured data.",
            )
        except Exception as e:
            run.status = RunStatus.FAILED.value
            run.current_stage = RunStage.FAILED.value
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await self._emit(run, RunStage.FAILED, StageEventStatus.ERROR, f"Processing failed: {e}")
            raise

    async def _consume_po_balance(self, po: PurchaseOrder, invoice) -> None:
        if invoice.total:
            po.remaining_value = max(Decimal("0"), po.remaining_value - invoice.total)
            if po.remaining_value == 0:
                po.status = "closed"
            elif po.remaining_value < po.total_value:
                po.status = "partial"
        for il in invoice.lines:
            if not il.item_code or not il.quantity:
                continue
            for pl in po.lines:
                if pl.item_code and il.item_code.lower() == pl.item_code.lower():
                    pl.invoiced_qty += il.quantity
                    pl.remaining_qty = max(Decimal("0"), pl.remaining_qty - il.quantity)

    async def _persist_invoice(self, run: ProcessingRun, invoice, vendor_id: str | None, po_id: str | None, decision: str) -> None:
        existing = await self.session.scalar(
            select(Invoice).where(Invoice.run_id == run.run_id)
        )
        if existing:
            return
        inv = Invoice(
            run_id=run.run_id,
            vendor_id=vendor_id,
            vendor_name=invoice.vendor_name,
            normalized_invoice_number=normalized_invoice_number(invoice),
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            tax=invoice.tax,
            total=invoice.total,
            po_reference=invoice.po_reference,
            matched_po_id=po_id,
            file_hash=run.file_hash,
            decision=decision,
        )
        self.session.add(inv)
        await self.session.flush()
        for line in invoice.lines:
            self.session.add(
                InvoiceLine(
                    invoice_id=inv.invoice_id,
                    description=line.description,
                    item_code=line.item_code,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    tax_rate=line.tax_rate,
                    line_total=line.line_total,
                )
            )
