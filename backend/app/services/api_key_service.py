"""
API key service — create, validate, and revoke API keys.

Keys are stored as SHA-256 hashes. The raw key is shown once on creation
and never stored. Format: lq_live_{32 random chars}
"""
import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)

KEY_PREFIX = "lq_"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> Tuple[str, str, str]:
    """Generate a new API key. Returns (raw_key, key_hash, key_prefix)."""
    random_part = secrets.token_urlsafe(32)
    raw_key = f"{KEY_PREFIX}{random_part}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


async def create_api_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    name: str,
) -> Tuple[ApiKey, str]:
    """Create a new API key. Returns (ApiKey record, raw_key). Raw key shown once only."""
    raw_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by=created_by,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    logger.info(f"[api-key] Created key '{name}' for tenant {tenant_id}")
    return api_key, raw_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[ApiKey]:
    """Validate an API key. Returns the ApiKey record if valid, None if not."""
    if not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        await db.commit()
    return api_key


async def revoke_api_key(db: AsyncSession, key_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
    """Revoke an API key. Returns True if found and revoked."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return False
    api_key.is_active = False
    await db.commit()
    logger.info(f"[api-key] Revoked key {key_id}")
    return True


async def list_api_keys(db: AsyncSession, tenant_id: uuid.UUID) -> list[ApiKey]:
    """List all active API keys for a tenant."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()
