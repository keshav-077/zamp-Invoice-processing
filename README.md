# Invoice Processing — From PDF to Decision

Explainable invoice-processing workflow for AP teams. Upload a vendor invoice PDF or image, extract fields via multimodal AI, match to purchase orders with deterministic controls, and receive **APPROVE**, **REVIEW**, or **REJECT** with full evidence.

## Architecture

- **Frontend:** Next.js 15 + TypeScript + Tailwind (`apps/web`)
- **Backend:** FastAPI + Python (`apps/api`)
- **Database:** SQLite (local dev) or PostgreSQL (Docker/production)
- **AI:** Gemini primary with Groq/OpenRouter fallbacks; mock extraction for CI without API keys

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

## Supported Upload Formats

- PDF (multi-page, up to 10 pages)
- PNG, JPG/JPEG, WebP (single-page image invoices)
- Max file size: 20 MB

## API Endpoints

- `POST /api/runs` — upload invoice PDF or image
- `GET /api/runs/{id}` — run detail + evidence
- `GET /api/runs/{id}/events/stream` — SSE live timeline
- `POST /api/runs/{id}/review` — manual review/override
- `GET /api/vendors`, `GET /api/pos` — reference data
- `GET /api/health` — health check

## Deploy to Railway

Deploy the full stack (API + web + Postgres) on [Railway](https://railway.app).

### 1. Create project

1. Push this repo to GitHub.
2. Create a new Railway project and connect the repository.
3. Add a **PostgreSQL** plugin to the project.

### 2. API service

1. Add a service from the repo with **Root Directory** set to the repository root.
2. Set **Config file** to `apps/api/railway.toml` (or use Dockerfile `apps/api/Dockerfile`).
3. Attach a **volume** mounted at `/data/uploads`.
4. Set environment variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (convert to `postgresql+asyncpg://...`) |
| `STORAGE_PATH` | `/data/uploads` |
| `CORS_ORIGINS` | Your Railway web service URL |
| `USE_MOCK_EXTRACTION` | `false` |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` | At least one required |
| `JWT_SECRET` | Strong random secret |

5. Generate a public domain for the API service.

### 3. Web service

1. Add a second service with **Root Directory** `apps/web`.
2. Set **Config file** to `apps/web/railway.toml`.
3. Set build variable `NEXT_PUBLIC_API_URL` to the API service public URL.
4. Generate a public domain for the web service.

### 4. Finalize CORS

Update the API service `CORS_ORIGINS` to the web service public URL and redeploy if needed.

### Smoke test

- `GET https://<api-domain>/api/health` returns healthy
- Open `https://<web-domain>/process` and upload a PDF or PNG

### CLI helper

After installing the Railway CLI (`npm install -g @railway/cli`) and running `railway login`:

```powershell
.\scripts\deploy-railway.ps1
```

Then complete the service setup steps printed by the script in the Railway dashboard.

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
