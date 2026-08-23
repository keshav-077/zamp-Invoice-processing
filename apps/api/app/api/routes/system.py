from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db, engine
from app.domain.schemas import HealthResponse, TokenRequest, TokenResponse
from app.services.auth import authenticate_user, create_access_token, ensure_demo_users
from app.domain.enums import UserRole

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    db_status = "healthy"
    try:
        await db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    providers = []
    if settings.gemini_api_key:
        providers.append("gemini")
    if settings.groq_api_key:
        providers.append("groq")
    if settings.openrouter_api_key:
        providers.append("openrouter")
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        extraction_mode="mock" if settings.use_mock_extraction else "live",
        providers_configured=providers,
    )


@router.post("/api/auth/login", response_model=TokenResponse)
async def login(body: TokenRequest, db: AsyncSession = Depends(get_db)):
    await ensure_demo_users(db)
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.username, user.role)
    return TokenResponse(access_token=token, role=UserRole(user.role), username=user.username)
