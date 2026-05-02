import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    register_tenant, verify_email, login_user, verify_totp_login, AuthError
)
from app.core.dependencies import get_current_user, CurrentUser

router = APIRouter()


class VerifyEmailRequest(BaseModel):
    user_id: str
    code: str


class TotpSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str


class TotpVerifyRequest(BaseModel):
    user_id: str
    code: str


class TotpEnableRequest(BaseModel):
    code: str


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new organisation and admin user.
    Sends a verification email. User must verify before logging in.
    """
    try:
        result = await register_tenant(db, data)
        return {
            "message": "Account created. Please check your email for a verification code.",
            "user_id": result["user_id"],
            "email": result["email"],
            "email_sent": result.get("email_sent", False),
            **({"dev_code": result["dev_code"]} if result.get("dev_code") else {}),
        }
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email_endpoint(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify email with 6-digit code. Issues JWT on success."""
    try:
        return await verify_email(db, data.user_id, data.code)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email + password.
    If 2FA is enabled, returns requires_totp=True and an empty token.
    Frontend should then prompt for TOTP code.
    """
    try:
        return await login_user(db, data)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/verify-totp", response_model=TokenResponse)
async def verify_totp_endpoint(data: TotpVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Complete login by submitting TOTP code from authenticator app."""
    try:
        return await verify_totp_login(db, data.user_id, data.code)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the currently authenticated user's profile."""
    from sqlalchemy import select
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=str(user.role).replace("UserRole.", ""),
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
    )


@router.get("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and QR code for the current user."""
    from sqlalchemy import select
    from app.models.user import User
    from app.services.totp_service import generate_totp_secret, generate_qr_code_base64

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.commit()

    qr = generate_qr_code_base64(secret, user.email)
    return TotpSetupResponse(secret=secret, qr_code_base64=qr)


@router.post("/totp/enable")
async def totp_enable(
    data: TotpEnableRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable 2FA by verifying the first TOTP code from the authenticator app."""
    from sqlalchemy import select
    from app.models.user import User
    from app.services.totp_service import verify_totp_code

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.totp_secret:
        raise HTTPException(400, "TOTP setup not initiated")

    if not verify_totp_code(user.totp_secret, data.code):
        raise HTTPException(400, "Invalid code — make sure your authenticator app is synced")

    user.totp_enabled = True
    await db.commit()
    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/totp/disable")
async def totp_disable(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA for the current user."""
    from sqlalchemy import select
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    return {"message": "Two-factor authentication disabled"}


@router.post("/oauth/complete-registration")
async def complete_oauth_registration(data: dict, db: AsyncSession = Depends(get_db)):
    """Complete registration for new OAuth users."""
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from app.models.tenant import Tenant
    from app.core.security import create_access_token
    from app.core.config import get_settings

    settings = get_settings()
    email = data.get("email", "").strip()
    full_name = data.get("full_name", "").strip()
    tenant_name = data.get("tenant_name", "").strip()
    tenant_slug = data.get("tenant_slug", "").strip()
    provider = data.get("provider", "google")

    if not all([email, tenant_name, tenant_slug]):
        raise HTTPException(400, "email, tenant_name and tenant_slug are required")

    existing_slug = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    if existing_slug.scalar_one_or_none():
        raise HTTPException(409, f"Workspace URL '{tenant_slug}' is already taken")

    existing_user = await db.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(409, "An account with this email already exists")

    tenant = Tenant(id=uuid.uuid4(), name=tenant_name, slug=tenant_slug, plan="starter", data_region="eu-west-2")
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email=email,
        full_name=full_name or None, role=UserRole.TENANT_ADMIN,
        is_active=True, email_verified=True, sso_provider=provider,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return {"access_token": token, "token_type": "bearer"}