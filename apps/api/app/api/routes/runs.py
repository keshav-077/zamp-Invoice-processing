import asyncio
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import ProcessingRun, RunEvent, POCandidateRecord, ValidationResultRecord, DuplicateMatchRecord, DecisionAudit
from app.db.session import get_db, AsyncSessionLocal
from app.domain.enums import RunStatus
from app.domain.schemas import RunCreateResponse, RunDetail, RunSummary
from app.services.documents import DocumentProcessor, is_allowed_extension
from app.services.workflow import WorkflowOrchestrator

router = APIRouter(prefix="/api/runs", tags=["runs"])
doc_processor = DocumentProcessor()
logger = logging.getLogger(__name__)


async def _run_workflow(run_id: str) -> None:
    async with AsyncSessionLocal() as session:
        orchestrator = WorkflowOrchestrator(session)
        try:
            await orchestrator.process_run(run_id)
            await session.commit()
        except Exception:
            logger.exception("Invoice workflow failed for run_id=%s", run_id)
            await session.commit()


@router.post("", response_model=RunCreateResponse)
async def create_run(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not file.filename or not is_allowed_extension(file.filename):
        raise HTTPException(status_code=400, detail="Only PDF, PNG, JPG, and WebP files are accepted.")
    content = await file.read()
    run = ProcessingRun(file_name=file.filename, status=RunStatus.PENDING.value)
    db.add(run)
    await db.flush()
    try:
        file_path, file_hash, page_count = doc_processor.save_upload(run.run_id, file.filename, content)
        run.file_path = file_path
        run.file_hash = file_hash
        run.page_count = page_count
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    asyncio.create_task(_run_workflow(run.run_id))
    return RunCreateResponse(run_id=run.run_id, status=RunStatus.RUNNING, created_at=run.created_at)


@router.get("", response_model=list[RunSummary])
async def list_runs(
    decision: str | None = None,
    vendor: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(ProcessingRun).order_by(ProcessingRun.created_at.desc()).limit(limit).offset(offset)
    if decision:
        query = query.where(ProcessingRun.decision == decision)
    if vendor:
        query = query.where(ProcessingRun.vendor_name.ilike(f"%{vendor}%"))
    if status:
        query = query.where(ProcessingRun.status == status)
    result = await db.execute(query)
    runs = result.scalars().all()
    return [
        RunSummary(
            run_id=r.run_id,
            status=RunStatus(r.status),
            decision=r.decision,
            vendor_name=r.vendor_name,
            invoice_number=r.invoice_number,
            total=r.total,
            currency=r.currency,
            po_id=r.matched_po_id,
            created_at=r.created_at,
            completed_at=r.completed_at,
            processing_time_ms=r.processing_time_ms,
            reason_codes=r.reason_codes or [],
        )
        for r in runs
    ]


async def _build_run_detail(run: ProcessingRun, db: AsyncSession) -> RunDetail:
    events_result = await db.execute(select(RunEvent).where(RunEvent.run_id == run.run_id).order_by(RunEvent.sequence))
    events = events_result.scalars().all()
    candidates_result = await db.execute(select(POCandidateRecord).where(POCandidateRecord.run_id == run.run_id).order_by(POCandidateRecord.rank))
    candidates = candidates_result.scalars().all()
    validations_result = await db.execute(select(ValidationResultRecord).where(ValidationResultRecord.run_id == run.run_id))
    validations = validations_result.scalars().all()
    dups_result = await db.execute(select(DuplicateMatchRecord).where(DuplicateMatchRecord.run_id == run.run_id))
    dups = dups_result.scalars().all()
    audits_result = await db.execute(select(DecisionAudit).where(DecisionAudit.run_id == run.run_id).order_by(DecisionAudit.created_at))
    audits = audits_result.scalars().all()
    match_result = next(
        (
            event.data
            for event in reversed(events)
            if event.stage == "po_match"
            and event.data
            and event.data.get("status")
        ),
        None,
    )

    return RunDetail(
        run_id=run.run_id,
        status=RunStatus(run.status),
        current_stage=run.current_stage,
        decision=run.decision,
        automated_decision=run.automated_decision,
        reason_codes=run.reason_codes or [],
        human_reason=run.human_reason,
        vendor_name=run.vendor_name,
        invoice_number=run.invoice_number,
        total=run.total,
        currency=run.currency,
        po_id=run.matched_po_id,
        match_status=match_result.get("status") if match_result else None,
        match_result=match_result,
        file_name=run.file_name,
        page_count=run.page_count,
        created_at=run.created_at,
        completed_at=run.completed_at,
        processing_time_ms=run.processing_time_ms,
        error_message=run.error_message,
        events=[{"stage": e.stage, "status": e.status, "message": e.message, "data": e.data, "timestamp": e.created_at.isoformat()} for e in events],
        extraction=run.extraction_data,
        model_metadata=run.model_metadata,
        normalized_invoice=run.normalized_invoice,
        vendor_resolution=run.vendor_resolution,
        po_candidates=[{"po_id": c.po_id, "total_score": float(c.total_score), "rank": c.rank, "signals": c.signals, "hard_constraints_pass": c.hard_constraints_pass, "hard_constraint_failures": c.hard_constraint_failures, "selected": c.selected} for c in candidates],
        validation_checks=[{"rule_id": v.rule_id, "name": v.name, "result": v.result, "message": v.message, "invoice_value": v.invoice_value, "po_value": v.po_value, "blocking": v.blocking} for v in validations],
        duplicate_matches=[{"match_type": d.match_type, "matched_run_id": d.matched_run_id, "confidence": float(d.confidence), "evidence": d.evidence} for d in dups],
        audit_trail=[{"actor": a.actor, "action": a.action, "old_value": a.old_value, "new_value": a.new_value, "reason": a.reason, "timestamp": a.created_at.isoformat()} for a in audits],
    )


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(ProcessingRun).where(ProcessingRun.run_id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await _build_run_detail(run, db)


@router.get("/{run_id}/evidence", response_model=RunDetail)
async def get_evidence(run_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await get_run(run_id, db, user)


@router.get("/{run_id}/events")
async def get_events(run_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.sequence))
    events = result.scalars().all()
    return [{"stage": e.stage, "status": e.status, "message": e.message, "data": e.data, "timestamp": e.created_at.isoformat()} for e in events]
