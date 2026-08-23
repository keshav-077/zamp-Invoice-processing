from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.domain.enums import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_USERS = [
    {"username": "analyst", "password": "analyst123", "role": UserRole.ANALYST},
    {"username": "manager", "password": "manager123", "role": UserRole.MANAGER},
    {"username": "admin", "password": "admin123", "role": UserRole.ADMIN},
    {"username": "auditor", "password": "auditor123", "role": UserRole.AUDITOR},
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def ensure_demo_users(session: AsyncSession) -> None:
    for u in DEMO_USERS:
        result = await session.execute(select(User).where(User.username == u["username"]))
        if not result.scalar_one_or_none():
            session.add(User(username=u["username"], password_hash=hash_password(u["password"]), role=u["role"].value))
    await session.commit()


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
