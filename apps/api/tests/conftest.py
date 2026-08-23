import os

# Tests must not call external LLM APIs even when repo .env disables mock mode.
os.environ["USE_MOCK_EXTRACTION"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AMOUNT_TOLERANCE_PERCENT"] = "2.0"
os.environ["AMOUNT_TOLERANCE_ABSOLUTE"] = "50.0"
os.environ["ROUNDING_TOLERANCE"] = "0.05"
os.environ["PO_MATCH_MIN_SCORE"] = "0.85"
os.environ["PO_MATCH_MIN_MARGIN"] = "0.10"
os.environ["EXTRACTION_CONFIDENCE_THRESHOLD"] = "0.75"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.config import get_settings
from app.db.models import Base
from app.db.session import get_db
from app.fixtures.seed import seed_reference_data
from extraction_fixtures import extract_for_test

get_settings.cache_clear()

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await seed_reference_data(session)
        yield session, session_factory, engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    session, session_factory, engine = db_session

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    import app.db.session as session_module
    import app.api.routes.runs as runs_module
    import app.services.workflow as workflow_module

    original_local = session_module.AsyncSessionLocal
    original_extractor = workflow_module.extract_with_fallback
    original_background_workflow = runs_module._run_workflow

    async def skip_background_workflow(run_id: str) -> None:
        return None

    session_module.AsyncSessionLocal = session_factory
    workflow_module.AsyncSessionLocal = session_factory
    workflow_module.extract_with_fallback = extract_for_test
    runs_module._run_workflow = skip_background_workflow

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    session_module.AsyncSessionLocal = original_local
    workflow_module.AsyncSessionLocal = original_local
    workflow_module.extract_with_fallback = original_extractor
    runs_module._run_workflow = original_background_workflow
    app.dependency_overrides.clear()
