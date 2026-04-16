import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# Extracts Bearer token from Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """
    Represents the authenticated user on a request.
    Populated from the JWT — no DB hit required for basic auth.
    """
    def __init__(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        role: UserRole,
        email: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.email = email

    def is_tenant_admin(self) -> bool:
        return self.role == UserRole.TENANT_ADMIN

    def is_editor_or_above(self) -> bool:
        return self.role in (
            UserRole.EDITOR,
            UserRole.MATTER_ADMIN,
            UserRole.TENANT_ADMIN,
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    FastAPI dependency — validates JWT and returns the current user.

    Usage in any endpoint:
        @router.get("/protected")
        async def protected(user: CurrentUser = Depends(get_current_user)):
            return {"tenant": str(user.tenant_id)}

    What it does:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes and verifies the JWT signature + expiry
    3. Sets the Postgres RLS context (app.current_tenant_id)
       so row-level security activates for this request
    4. Returns a CurrentUser object with user_id, tenant_id, role
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: Optional[str] = payload.get("sub")
        tenant_id_str: Optional[str] = payload.get("tenant_id")
        role_str: Optional[str] = payload.get("role")

        if not user_id_str or not tenant_id_str or not role_str:
            raise credentials_exception

        user_id = uuid.UUID(user_id_str)
        tenant_id = uuid.UUID(tenant_id_str)
        role = UserRole(role_str)

    except (JWTError, ValueError, KeyError):
        raise credentials_exception

    # Set Postgres RLS context so tenant isolation activates
    # Every query in this request will only see rows where
    # tenant_id matches the current user's tenant
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )

    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
    )


async def require_tenant_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency — endpoint requires Tenant Admin role."""
    if not current_user.is_tenant_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant Admin role required",
        )
    return current_user


async def require_editor(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency — endpoint requires Editor role or above."""
    if not current_user.is_editor_or_above():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor role or above required",
        )
    return current_user
