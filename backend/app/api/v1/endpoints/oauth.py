"""
OAuth endpoints — Google and Microsoft.
"""
import secrets
import traceback
import uuid
import logging
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.core.security import create_access_token
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

FRONTEND_CALLBACK = "http://localhost:3000/auth/callback"
_oauth_states: dict[str, str] = {}


@router.get("/google/login")
async def google_login():
    if not settings.google_client_id:
        raise HTTPException(400, "Google OAuth not configured")
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = "google"
    from urllib.parse import urlencode
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None, db: AsyncSession = Depends(get_db)):
    logger.info(f"[oauth] Callback received — code={bool(code)} state={bool(state)} error={error}")
    if error:
        return RedirectResponse(f"{FRONTEND_CALLBACK}?error=google_denied")
    if state and state in _oauth_states:
        _oauth_states.pop(state)
    elif not state:
        return RedirectResponse(f"{FRONTEND_CALLBACK}?error=invalid_state")
    if not code:
        return RedirectResponse(f"{FRONTEND_CALLBACK}?error=no_code")
    logger.info(f"[oauth] Exchanging code with Google...")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            logger.info(f"[oauth] Token response status: {token_res.status_code}")
            if not token_res.is_success:
                logger.error(f"[oauth] Token exchange failed: {token_res.text}")
                return RedirectResponse(f"{FRONTEND_CALLBACK}?error=token_exchange_failed")
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            logger.info(f"[oauth] Got access token: {bool(access_token)}")
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo = userinfo_res.json()
            logger.info(f"[oauth] Got userinfo: {userinfo.get('email')}")
    except Exception as e:
        logger.error(f"[oauth] Google exchange error: {e}\n{traceback.format_exc()}")
        return RedirectResponse(f"{FRONTEND_CALLBACK}?error=google_failed")

    email = userinfo.get("email")
    name = userinfo.get("name", "")
    if not email:
        return RedirectResponse(f"{FRONTEND_CALLBACK}?error=no_email")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if not user.is_active:
            return RedirectResponse(f"{FRONTEND_CALLBACK}?error=account_inactive")
        token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
        logger.info(f"[oauth] Redirecting to frontend with token for {email}")
        return RedirectResponse(f"{FRONTEND_CALLBACK}?token={token}")
    else:
        logger.info(f"[oauth] New Google user — redirecting to org setup: {email}")
        return RedirectResponse(
            f"{FRONTEND_CALLBACK}?oauth_email={quote(email)}&oauth_name={quote(name)}&provider=google"
        )


@router.get("/microsoft/login")
async def microsoft_login():
    raise HTTPException(501, "Microsoft OAuth not yet configured")


@router.get("/microsoft/callback")
async def microsoft_callback():
    return RedirectResponse(f"{FRONTEND_CALLBACK}?error=microsoft_not_configured")


@router.post("/oauth/complete-registration")
async def complete_oauth_registration(data: dict, db: AsyncSession = Depends(get_db)):
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
