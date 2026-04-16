from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
import httpx

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Service health check. Verifies connectivity to all infrastructure
    dependencies. Used by load balancers and monitoring.
    """
    status = {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "dependencies": {},
    }

    # Postgres
    try:
        await db.execute(text("SELECT 1"))
        status["dependencies"]["postgres"] = "ok"
    except Exception as e:
        status["dependencies"]["postgres"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
        status["dependencies"]["redis"] = "ok"
    except Exception as e:
        status["dependencies"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Weaviate
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.weaviate_url}/v1/.well-known/ready")
            if resp.status_code == 200:
                status["dependencies"]["weaviate"] = "ok"
            else:
                status["dependencies"]["weaviate"] = f"http {resp.status_code}"
                status["status"] = "degraded"
    except Exception as e:
        status["dependencies"]["weaviate"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status
