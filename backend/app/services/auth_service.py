import uuid
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
) -> TokenResponse:
    """
    Onboarding flow:
    1. Check slug is not already taken
    2. Create the Tenant record
    3. Create the first Tenant Admin user
    4. Return a JWT so the user is immediately logged in
    """

    # Check slug uniqueness
    existing = await db.execute(
        select(Tenant).where(Tenant.slug == data.tenant_slug)
    )
    if existing.scalar_one_or_none():
        raise AuthError(
            f"Tenant slug '{data.tenant_slug}' is already taken",
            status_code=409,
        )

    # Check email uniqueness
    existing_user = await db.execute(
        select(User).where(User.email == data.email)
    )
    if existing_user.scalar_one_or_none():
        raise AuthError(
            f"Email '{data.email}' is already registered",
            status_code=409,
        )

    # Create tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name=data.tenant_name,
        slug=data.tenant_slug,
        plan="starter",
        data_region="eu-west-2",
    )
    db.add(tenant)
    await db.flush()  # get tenant.id without committing yet

    # Create first admin user
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.TENANT_ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Issue JWT immediately — user is logged in on registration
    token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role,
    )


async def login_user(
    db: AsyncSession,
    data: LoginRequest,
) -> TokenResponse:
    """
    Login flow:
    1. Look up user by email
    2. Verify password against bcrypt hash
    3. Check user and tenant are active
    4. Return a signed JWT
    """

    # Look up user
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user: Optional[User] = result.scalar_one_or_none()

    # Deliberately vague error — don't reveal whether email exists
    if not user or not user.hashed_password:
        raise AuthError("Invalid email or password")

    if not verify_password(data.password, user.hashed_password):
        raise AuthError("Invalid email or password")

    if not user.is_active:
        raise AuthError("Account is deactivated. Contact your administrator.")

    # Check tenant is still active
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant: Optional[Tenant] = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise AuthError("Your organisation account is not active.")

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )
