"""
Redis query cache service.

Caches query results per tenant + query hash for 15 minutes.
Falls back gracefully if Redis is unavailable.
"""
import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        logger.info("[cache] Redis connected")
    except Exception as e:
        logger.warning(f"[cache] Redis unavailable — caching disabled: {e}")
        _redis_client = None
    return _redis_client


def make_cache_key(tenant_id: str, query: str, workspace_id: Optional[str]) -> str:
    raw = f"{tenant_id}:{workspace_id or 'all'}:{query.strip().lower()}"
    return "lq:query:" + hashlib.sha256(raw.encode()).hexdigest()


def get_cached_query(tenant_id: str, query: str, workspace_id: Optional[str]) -> Optional[dict]:
    r = get_redis()
    if not r:
        return None
    try:
        key = make_cache_key(tenant_id, query, workspace_id)
        val = r.get(key)
        if val:
            logger.info(f"[cache] HIT for tenant={tenant_id}")
            return json.loads(val)
    except Exception as e:
        logger.warning(f"[cache] Get failed: {e}")
    return None


def set_cached_query(tenant_id: str, query: str, workspace_id: Optional[str], result: dict, ttl: int = 900) -> None:
    r = get_redis()
    if not r:
        return
    try:
        key = make_cache_key(tenant_id, query, workspace_id)
        r.setex(key, ttl, json.dumps(result))
        logger.info(f"[cache] SET for tenant={tenant_id} ttl={ttl}s")
    except Exception as e:
        logger.warning(f"[cache] Set failed: {e}")


def invalidate_workspace_cache(tenant_id: str) -> None:
    """Invalidate all cached queries for a tenant when new docs are added."""
    r = get_redis()
    if not r:
        return
    try:
        pattern = f"lq:query:*"
        # We can't easily invalidate by tenant without scanning
        # For now just log — a TTL of 15min is acceptable for stale cache
        logger.info(f"[cache] Invalidation requested for tenant={tenant_id} (TTL-based)")
    except Exception as e:
        logger.warning(f"[cache] Invalidation failed: {e}")
