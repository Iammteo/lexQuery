import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import get_settings
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

settings = get_settings()


class AuthError(Exception):
    """Raised for authentication/authorisation failures."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def register_tenant(
    db: AsyncSession,
    data: RegisterRequest,
) -> dict:
    """
    Onboarding flow:
    1. Check slug and email are not already taken
    2. Create the Tenant record
    3. Create the first Tenant Admin user
    4. Send verification email
    5. Return user_id so frontend can show verification step
    """
    existing = await db.execute(select(Tenant).where(Tenant.slug == data.tenant_slug))
    if existing.scalar_one_or_none():
        raise AuthError(f"Workspace URL '{data.tenant_slug}' is already taken", status_code=409)

    existing_user = await db.execute(select(User).where(User.email == data.email))
    if existing_user.scalar_one_or_none():
        raise AuthError(f"Email '{data.email}' is already registered", status_code=409)

    from app.services.email_service import generate_verification_code
    code = generate_verification_code()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    tenant = Tenant(
        id=uuid.uuid4(), name=data.tenant_name, slug=data.tenant_slug,
        plan="starter", data_region="eu-west-2",
        subscription_status="trialing", current_plan="trial",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email=data.email,
        hashed_password=hash_password(data.password), full_name=data.full_name,
        role=UserRole.TENANT_ADMIN, is_active=True, email_verified=False,
        verification_code=code, verification_code_expires=expires,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    email_sent = False
    dev_code = None
    try:
        from app.services.email_service import send_verification_email
        send_verification_email(data.email, code, data.full_name or "")
        email_sent = True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[auth] Email send failed: {e}")
        dev_code = code  # surface in response for dev mode

    return {
        "user_id": str(user.id),
        "email": data.email,
        "email_sent": email_sent,
        **({"dev_code": dev_code} if dev_code else {}),
    }


async def verify_email(
    db: AsyncSession,
    user_id: str,
    code: str,
) -> TokenResponse:
    """Verify the 6-digit email code and issue a JWT."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise AuthError("Invalid user ID", 400)

    result = await db.execute(select(User).where(User.id == uid))
    user: Optional[User] = result.scalar_one_or_none()

    if not user:
        raise AuthError("User not found", 404)

    if user.email_verified:
        # Already verified — just issue a token
        token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
        return TokenResponse(
            access_token=token,
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=str(user.role).replace("UserRole.", ""),
            requires_totp=False,
        )

    if user.verification_code != code:
        raise AuthError("Invalid verification code", 400)

    if user.verification_code_expires:
        try:
            expires = datetime.fromisoformat(user.verification_code_expires)
            if datetime.now(timezone.utc) > expires:
                raise AuthError("Verification code has expired. Please register again.", 400)
        except ValueError:
            pass

    user.email_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=str(user.role).replace("UserRole.", ""),
        requires_totp=False,
    )


async def login_user(
    db: AsyncSession,
    data: LoginRequest,
) -> TokenResponse:
    """
    Login flow:
    1. Look up user by email
    2. Verify password
    3. Check email is verified
    4. Check user and tenant are active
    5. If TOTP enabled, return requires_totp=True
    6. Otherwise return JWT
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user: Optional[User] = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise AuthError("Invalid email or password")

    if not verify_password(data.password, user.hashed_password):
        raise AuthError("Invalid email or password")

    if not user.email_verified:
        raise AuthError("Please verify your email address before signing in.", 403)

    if not user.is_active:
        raise AuthError("Account is deactivated. Contact your administrator.")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant: Optional[Tenant] = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise AuthError("Your organisation account is not active.")

    # If TOTP enabled, don't issue a full token yet
    if user.totp_enabled:
        return TokenResponse(
            access_token="",
            expires_in=0,
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=str(user.role).replace("UserRole.", ""),
            requires_totp=True,
        )

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=str(user.role).replace("UserRole.", ""),
        requires_totp=False,
    )


async def verify_totp_login(
    db: AsyncSession,
    user_id: str,
    code: str,
) -> TokenResponse:
    """Complete login by verifying TOTP code and issuing JWT."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise AuthError("Invalid user ID", 400)

    result = await db.execute(select(User).where(User.id == uid))
    user: Optional[User] = result.scalar_one_or_none()

    if not user:
        raise AuthError("User not found", 404)

    if not user.totp_secret:
        raise AuthError("2FA is not configured for this account", 400)

    from app.services.totp_service import verify_totp_code
    if not verify_totp_code(user.totp_secret, code):
        raise AuthError("Invalid authenticator code", 400)

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=str(user.role).replace("UserRole.", ""),
        requires_totp=False,
    )


# ── In-memory invite store ────────────────────────────────────────
_invites: dict = {}

async def create_invite(db, tenant_id, invitee_email: str, role: str, invited_by_user_id=None, invited_by=None):
    email = invitee_email
    import secrets
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    _invites[token] = {
        "tenant_id": str(tenant_id),
        "email": email,
        "role": role,
        "invited_by": str(invited_by),
        "expires": expires,
    }
    try:
        from app.services.email_service import send_invite_email
        send_invite_email(email, "", "", role, token)
    except Exception:
        pass
    return token


async def accept_invite(db, token: str, full_name: str, password: str):
    from sqlalchemy import select as _select
    data = _invites.get(token)
    if not data:
        raise AuthError("Invalid or expired invite link", 400)

    expires = datetime.fromisoformat(data["expires"])
    if datetime.now(timezone.utc) > expires:
        raise AuthError("This invitation has expired", 400)

    existing = await db.execute(_select(User).where(User.email == data["email"]))
    if existing.scalar_one_or_none():
        raise AuthError("An account with this email already exists", 409)

    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(data["tenant_id"]),
        email=data["email"],
        hashed_password=hash_password(password),
        full_name=full_name,
        role=data["role"],
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    _invites.pop(token, None)

    token_str = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenResponse(
        access_token=token_str,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=str(user.role).replace("UserRole.", ""),
        requires_totp=False,
    )