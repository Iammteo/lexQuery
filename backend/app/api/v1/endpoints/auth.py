from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_tenant, login_user, AuthError
from app.core.dependencies import get_current_user, CurrentUser

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Onboard a new organisation.

    Creates a new Tenant and its first Tenant Admin user in one step.
    Returns a JWT so the user is immediately authenticated.

    Example request:
    {
        "tenant_name": "Acme Legal",
        "tenant_slug": "acme-legal",
        "email": "admin@acmelegal.com",
        "password": "securepassword",
        "full_name": "Sarah Chen"
    }
    """
    try:
        return await register_tenant(db, data)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return a JWT access token.

    The token should be included in subsequent requests as:
        Authorization: Bearer <token>

    Token carries: user_id, tenant_id, role, expiry.
    Valid for 8 hours by default (configurable via ACCESS_TOKEN_EXPIRE_MINUTES).
    """
    try:
        return await login_user(db, data)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the currently authenticated user's profile.
    Requires a valid Bearer token.
    """
    from sqlalchemy import select
    from app.models.user import User

    result = await db.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
    )
