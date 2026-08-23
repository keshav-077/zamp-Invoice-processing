import io
import asyncio

import fitz
import pytest
from PIL import Image

from app.services.workflow import WorkflowOrchestrator


def _minimal_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "inv-001 demo invoice", fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _minimal_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="white").save(buf, format="PNG")
    return buf.getvalue()


def _minimal_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="white").save(buf, format="JPEG")
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


@pytest.mark.asyncio
async def test_upload_png(client, db_session):
    session, _, _ = db_session
    files = {"file": ("inv-001.png", io.BytesIO(_minimal_png()), "image/png")}
    resp = await client.post("/api/runs", files=files)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    orchestrator = WorkflowOrchestrator(session)
    await orchestrator.process_run(run_id)
    await session.commit()

    detail = await client.get(f"/api/runs/{run_id}")
    data = detail.json()
    assert data["status"] in ("completed", "review", "failed")
    assert len(data["events"]) > 0


@pytest.mark.asyncio
async def test_upload_jpeg(client, db_session):
    session, _, _ = db_session
    files = {"file": ("inv-001.jpg", io.BytesIO(_minimal_jpeg()), "image/jpeg")}
    resp = await client.post("/api/runs", files=files)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    orchestrator = WorkflowOrchestrator(session)
    await orchestrator.process_run(run_id)
    await session.commit()

    detail = await client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = await client.post("/api/runs", files=files)
    assert resp.status_code == 400
    assert "accepted" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_invalid_png(client):
    files = {"file": ("bad.png", io.BytesIO(b"not-a-png"), "image/png")}
    resp = await client.post("/api/runs", files=files)
    assert resp.status_code == 400
