from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.enums import UserRole
from app.services.auth import decode_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if not credentials:
        return {"username": "demo", "role": UserRole.ANALYST.value}
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"username": payload["sub"], "role": payload.get("role", UserRole.ANALYST.value)}


def require_roles(*roles: UserRole):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if UserRole(user["role"]) not in roles and user["role"] != UserRole.ADMIN.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
