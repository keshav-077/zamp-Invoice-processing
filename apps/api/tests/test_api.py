import io
import asyncio

import fitz
import pytest

from app.services.workflow import WorkflowOrchestrator


def _minimal_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "inv-001 demo invoice", fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("healthy", "degraded")
    assert resp.json()["extraction_mode"] == "mock"


@pytest.mark.asyncio
async def test_upload_happy_path(client, db_session):
    session, _, _ = db_session
    files = {"file": ("inv-001.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    resp = await client.post("/api/runs", files=files)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    orchestrator = WorkflowOrchestrator(session)
    await orchestrator.process_run(run_id)
    await session.commit()

    detail = await client.get(f"/api/runs/{run_id}")
    data = detail.json()
    assert data["status"] in ("completed", "review", "failed")
    assert data["decision"] in ("APPROVE", "REVIEW", "REJECT")
    assert len(data["events"]) > 0


@pytest.mark.asyncio
async def test_list_vendors(client):
    resp = await client.get("/api/vendors")
    assert resp.status_code == 200
    assert len(resp.json()) >= 8
