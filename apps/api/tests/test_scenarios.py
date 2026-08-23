import io
from decimal import Decimal

import fitz
import pytest
from sqlalchemy import select

from app.db.models import PurchaseOrder
from app.services.workflow import WorkflowOrchestrator


def _pdf(name: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), name, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


async def _process(
    client, db_session, filename: str, pdf_content: bytes | None = None
) -> dict:
    session, _, _ = db_session
    files = {
        "file": (
            filename,
            io.BytesIO(pdf_content if pdf_content is not None else _pdf(filename)),
            "application/pdf",
        )
    }
    resp = await client.post("/api/runs", files=files)
    run_id = resp.json()["run_id"]
    orchestrator = WorkflowOrchestrator(session)
    await orchestrator.process_run(run_id)
    await session.commit()
    detail = await client.get(f"/api/runs/{run_id}")
    return detail.json()


@pytest.mark.asyncio
async def test_inv001_approve(client, db_session):
    data = await _process(client, db_session, "inv-001.pdf")
    assert data["decision"] == "APPROVE"
    assert data["match_status"] == "MATCHED"
    assert data["po_id"] == "PO-1001"


@pytest.mark.asyncio
async def test_inv003_ambiguous_review(client, db_session):
    data = await _process(client, db_session, "inv-003.pdf")
    assert data["decision"] == "REVIEW"
    assert data["match_status"] == "POSSIBLE_MATCH"
    assert data["po_id"] is None
    assert "AMBIGUOUS_PO_MATCH" in data["reason_codes"]


@pytest.mark.asyncio
async def test_exact_duplicate_routes_to_review(client, db_session):
    content = _pdf("inv-001.pdf")
    await _process(client, db_session, "inv-001.pdf", content)
    data = await _process(client, db_session, "inv-001.pdf", content)
    assert data["decision"] == "REVIEW"
    assert "DUPLICATE_EXACT" in data["reason_codes"]


@pytest.mark.asyncio
async def test_inv008_low_confidence_review(client, db_session):
    data = await _process(client, db_session, "inv-008.pdf")
    assert data["decision"] == "REVIEW"


@pytest.mark.asyncio
async def test_unknown_vendor_and_weak_candidate_are_not_selected(client, db_session):
    data = await _process(client, db_session, "unknown-vendor.pdf")
    assert data["decision"] == "REVIEW"
    assert data["match_status"] == "NO_MATCH"
    assert data["po_id"] is None
    assert "VENDOR_UNRESOLVED" in data["reason_codes"]
    assert "NO_PO_MATCH" in data["reason_codes"]


@pytest.mark.asyncio
async def test_unrelated_closed_po_is_not_treated_as_match(client, db_session):
    data = await _process(client, db_session, "unrelated-closed.pdf")
    assert data["decision"] == "REVIEW"
    assert data["match_status"] == "NO_MATCH"
    assert data["po_id"] is None
    assert "PO_CLOSED" not in data["reason_codes"]


@pytest.mark.asyncio
async def test_explicit_closed_po_is_matched_then_rejected(client, db_session):
    data = await _process(client, db_session, "explicit-closed.pdf")
    assert data["decision"] == "REJECT"
    assert data["match_status"] == "MATCHED"
    assert data["po_id"] == "PO-1010"
    assert "PO_CLOSED" in data["reason_codes"]


@pytest.mark.asyncio
async def test_split_invoices_consume_remaining_balance(client, db_session):
    decisions = []
    balances = []
    session, _, _ = db_session
    for filename in ("split-1.pdf", "split-2.pdf", "split-3.pdf"):
        data = await _process(client, db_session, filename)
        decisions.append(data["decision"])
        po = await session.scalar(
            select(PurchaseOrder).where(PurchaseOrder.po_id == "PO-1005")
        )
        balances.append(str(po.remaining_value))

    assert decisions == ["APPROVE", "APPROVE", "APPROVE"]
    assert [Decimal(balance) for balance in balances] == [
        Decimal("10800.00"),
        Decimal("5400.00"),
        Decimal("0.00"),
    ]


@pytest.mark.asyncio
async def test_overage_routes_to_review_without_consuming_balance(client, db_session):
    data = await _process(client, db_session, "overage.pdf")
    session, _, _ = db_session
    po = await session.scalar(
        select(PurchaseOrder).where(PurchaseOrder.po_id == "PO-1005")
    )
    assert data["decision"] == "REVIEW"
    assert data["match_status"] == "MATCHED"
    assert "AMOUNT_OVER_TOLERANCE" in data["reason_codes"]
    assert str(po.remaining_value) == "16200.00"


@pytest.mark.asyncio
async def test_missing_tax_remains_null(client, db_session):
    data = await _process(client, db_session, "missing-tax.pdf")
    assert data["normalized_invoice"]["tax"] is None
