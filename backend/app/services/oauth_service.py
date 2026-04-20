"""
OAuth service for Google and Microsoft sign-in.

Flow:
  1. User clicks "Continue with Google" on frontend
  2. Frontend redirects to GET /v1/auth/google/login
  3. Backend redirects to Google consent screen
  4. Google redirects to GET /v1/auth/google/callback?code=xxx
  5. Backend exchanges code for user info (email, name)
  6. If user exists → issue JWT → redirect to /auth/callback?token=xxx
  7. If new user → redirect to /auth/callback?oauth_email=xxx&oauth_name=xxx&provider=google
  8. Frontend /auth/callback handles both cases:
     - Has token → store and go to dashboard
     - Has oauth_email → show mini org setup form, then register
"""
import httpx
import secrets
from urllib.parse import urlencode
from app.core.config import get_settings

settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"


def get_google_login_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> dict:
    """Exchange Google auth code for user info."""
    async with httpx.AsyncClient() as client:
        token_res = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })
        token_res.raise_for_status()
        token_data = token_res.json()

        userinfo_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json()

    return {
        "email": userinfo.get("email"),
        "name": userinfo.get("name", ""),
        "provider": "google",
        "provider_id": userinfo.get("sub"),
    }


def get_microsoft_login_url(state: str) -> str:
    params = {
        "client_id": settings.microsoft_client_id,
        "redirect_uri": settings.microsoft_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile User.Read",
        "state": state,
        "prompt": "select_account",
    }
    return f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"


async def exchange_microsoft_code(code: str) -> dict:
    """Exchange Microsoft auth code for user info."""
    async with httpx.AsyncClient() as client:
        token_res = await client.post(MICROSOFT_TOKEN_URL, data={
            "code": code,
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "redirect_uri": settings.microsoft_redirect_uri,
            "grant_type": "authorization_code",
            "scope": "openid email profile User.Read",
        })
        token_res.raise_for_status()
        token_data = token_res.json()

        userinfo_res = await client.get(
            MICROSOFT_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json()

    return {
        "email": userinfo.get("mail") or userinfo.get("userPrincipalName"),
        "name": userinfo.get("displayName", ""),
        "provider": "microsoft",
        "provider_id": userinfo.get("id"),
    }
