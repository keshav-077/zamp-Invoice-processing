import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.api.routes import runs, review, reference, system
from app.config import get_settings
from app.db.models import Base
from app.db.session import engine, AsyncSessionLocal
from app.services.auth import ensure_demo_users

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(levelname)s:     %(message)s",
)


def _log_extraction_mode() -> None:
    settings = get_settings()
    if settings.use_mock_extraction:
        logger.warning("USE_MOCK_EXTRACTION=true — using filename-based mock extraction, not LLM APIs")
        return
    providers = []
    if settings.gemini_api_key:
        providers.append(f"gemini ({settings.gemini_model})")
    if settings.groq_api_key:
        providers.append(f"groq ({settings.groq_model})")
    if settings.openrouter_api_key:
        providers.append(f"openrouter ({settings.openrouter_model})")
    if providers:
        logger.info("Live extraction enabled: %s", " -> ".join(providers))
    else:
        raise RuntimeError(
            "USE_MOCK_EXTRACTION=false but no LLM API keys are configured"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_extraction_mode()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await ensure_demo_users(session)
        from app.fixtures.seed import seed_reference_data
        await seed_reference_data(session)
    yield


app = FastAPI(title="Invoice Processing API", version="1.0.0", lifespan=lifespan)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(runs.router)
app.include_router(review.router)
app.include_router(reference.router)


@app.get("/api/runs/{run_id}/events/stream")
async def stream_events(run_id: str):
    from sqlalchemy import select
    from app.db.models import RunEvent, ProcessingRun

    async def event_generator():
        last_seq = 0
        for _ in range(120):
            async with AsyncSessionLocal() as session:
                run_result = await session.execute(select(ProcessingRun).where(ProcessingRun.run_id == run_id))
                run = run_result.scalar_one_or_none()
                if not run:
                    yield {"event": "error", "data": "Run not found"}
                    return
                events_result = await session.execute(
                    select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.sequence > last_seq).order_by(RunEvent.sequence)
                )
                events = events_result.scalars().all()
                for e in events:
                    last_seq = e.sequence
                    yield {
                        "event": "stage",
                        "data": json.dumps(
                            {
                                "stage": e.stage,
                                "status": e.status,
                                "message": e.message,
                            }
                        ),
                    }
                if run.status in ("completed", "failed", "review"):
                    yield {"event": "done", "data": run.status}
                    return
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
