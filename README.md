# Invoice Processing — From PDF to Decision

Explainable invoice-processing workflow for AP teams. Upload a vendor invoice PDF, extract fields via multimodal AI, match to purchase orders with deterministic controls, and receive **APPROVE**, **REVIEW**, or **REJECT** with full evidence.

## Architecture

- **Frontend:** Next.js 15 + TypeScript + Tailwind (`apps/web`)
- **Backend:** FastAPI + Python (`apps/api`)
- **Database:** SQLite (local dev) or PostgreSQL (Docker/production)
- **AI:** Gemini primary with Groq/OpenRouter fallbacks; mock extraction for CI/demo without API keys

## Quick Start

### 1. Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy ..\..\.env.example ..\..\.env
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Both apps load the repository-root `.env`. Relative SQLite and upload paths
resolve under `apps/api`, regardless of the directory used to start the API.

### 3. Docker (PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

## Demo Scenarios

Upload PDFs named by scenario (mock extraction maps filename → fixture data):

| File | Expected |
|------|----------|
| inv-001.pdf | APPROVE — exact PO match |
| inv-002.pdf | APPROVE — no PO number, vendor+amount match |
| inv-003.pdf | REVIEW — ambiguous POs |
| inv-004.pdf | APPROVE — split invoice |
| inv-005.pdf | REVIEW — over tolerance |
| inv-006.pdf | REJECT — duplicate |
| inv-007.pdf | REVIEW — wrong vendor |
| inv-008.pdf | REVIEW — low extraction confidence |

Generate demo PDFs:

```bash
cd apps/api
python scripts/generate_demo_pdfs.py
```

## Demo Accounts

| User | Password | Role |
|------|----------|------|
| analyst | analyst123 | AP Analyst |
| manager | manager123 | AP Manager |
| admin | admin123 | Admin |
| auditor | auditor123 | Auditor |

## API Endpoints

- `POST /api/runs` — upload invoice PDF
- `GET /api/runs/{id}` — run detail + evidence
- `GET /api/runs/{id}/events/stream` — SSE live timeline
- `POST /api/runs/{id}/review` — manual review/override
- `GET /api/vendors`, `GET /api/pos` — reference data
- `GET /api/health` — health check

## Design Principles

1. **Hybrid AI + rules:** VLM extracts; deterministic code decides money and policy
2. **Explainability:** Every decision has reason codes, validation checks, and PO candidate scores
3. **Safety:** Critical failures never auto-approve; duplicates block approval
4. **Auditability:** Immutable run events and override audit trail

## Tests

```bash
cd apps/api && pytest
cd apps/web && npm run build
```

## Environment Variables

See [`.env.example`](.env.example). Set `USE_MOCK_EXTRACTION=false` and provide
at least one provider API key for live multimodal extraction. Live mode fails
clearly when no provider is configured; it never silently substitutes demo data.
