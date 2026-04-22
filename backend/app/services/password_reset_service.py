"""
Password reset service.

Flow:
  1. User requests reset → token generated, email sent
  2. User clicks link → token validated
  3. User sets new password → token consumed, password updated

Tokens expire after 1 hour and are single-use.
"""
import uuid
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.security import hash_password

logger = logging.getLogger(__name__)

# In-memory store — use Redis in production
# Format: { token: { user_id, email, expires } }
_reset_tokens: dict = {}

TOKEN_EXPIRY_HOURS = 1


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """
    Generate a reset token and send reset email.
    Does NOT reveal whether the email exists — always returns success.
    """
    result = await db.execute(select(User).where(User.email == email))
    user: Optional[User] = result.scalar_one_or_none()

    if not user:
        # Don't reveal that email doesn't exist
        logger.info(f"[reset] Reset requested for unknown email: {email}")
        return

    token = _generate_token()
    expires = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()

    _reset_tokens[token] = {
        "user_id": str(user.id),
        "email": email,
        "expires": expires,
    }

    try:
        from app.services.email_service import send_password_reset_email
        send_password_reset_email(email, token, user.full_name or "")
        logger.info(f"[reset] Reset email sent to {email}")
    except Exception as e:
        logger.error(f"[reset] Failed to send reset email: {e}")
        _reset_tokens.pop(token, None)
        raise


def validate_reset_token(token: str) -> Optional[dict]:
    """Validate a reset token. Returns token data or None if invalid/expired."""
    data = _reset_tokens.get(token)
    if not data:
        return None

    expires = datetime.fromisoformat(data["expires"])
    if datetime.now(timezone.utc) > expires:
        _reset_tokens.pop(token, None)
        return None

    return data


async def reset_password(db: AsyncSession, token: str, new_password: str) -> bool:
    """
    Reset password using a valid token.
    Returns True if successful, False if token invalid/expired.
    """
    data = validate_reset_token(token)
    if not data:
        return False

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(data["user_id"]))
    )
    user: Optional[User] = result.scalar_one_or_none()
    if not user:
        return False

    user.hashed_password = hash_password(new_password)
    await db.commit()

    # Consume token — single use
    _reset_tokens.pop(token, None)
    logger.info(f"[reset] Password reset successful for {user.email}")
    return True
