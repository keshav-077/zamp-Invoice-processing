from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.db.models import DecisionAudit, ProcessingRun, PurchaseOrder, POCandidateRecord
from app.db.session import get_db
from app.domain.enums import Decision, UserRole
from app.domain.schemas import ReviewRequest

router = APIRouter(prefix="/api/runs", tags=["review"])


@router.post("/{run_id}/review")
async def submit_review(
    run_id: str,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles(UserRole.ANALYST, UserRole.MANAGER)),
):
    if not body.reason or len(body.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Review reason is required (minimum 5 characters).")

    result = await db.execute(select(ProcessingRun).where(ProcessingRun.run_id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    old_decision = run.decision
    old_po = run.matched_po_id

    if body.action == "select_po" and body.po_id:
        po_result = await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).where(PurchaseOrder.po_id == body.po_id))
        po = po_result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        run.matched_po_id = body.po_id
        cand_result = await db.execute(select(POCandidateRecord).where(POCandidateRecord.run_id == run_id))
        for c in cand_result.scalars().all():
            c.selected = c.po_id == body.po_id
        if run.decision in (Decision.REVIEW.value, None):
            run.decision = Decision.APPROVE.value
        run.human_reason = f"Manual PO selection: {body.po_id}. {body.reason}"
        db.add(DecisionAudit(run_id=run_id, actor=user["username"], action="select_po", old_value=old_po, new_value=body.po_id, reason=body.reason))

    elif body.action == "override_decision" and body.decision:
        if user["role"] not in (UserRole.MANAGER.value, UserRole.ADMIN.value):
            raise HTTPException(status_code=403, detail="Only managers can override decisions.")
        run.decision = body.decision.value
        run.human_reason = f"Manager override to {body.decision.value}: {body.reason}"
        db.add(DecisionAudit(run_id=run_id, actor=user["username"], action="override_decision", old_value=old_decision, new_value=body.decision.value, reason=body.reason))
    else:
        raise HTTPException(status_code=400, detail="Invalid review action.")

    run.status = "completed"
    await db.commit()
    return {"run_id": run_id, "decision": run.decision, "po_id": run.matched_po_id, "message": "Review submitted"}
