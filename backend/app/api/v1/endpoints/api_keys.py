import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.db.session import get_db
from app.core.dependencies import require_tenant_admin, CurrentUser
from app.services.api_key_service import create_api_key, revoke_api_key, list_api_keys

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateKeyRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[str]
    created_at: Optional[datetime]


class CreateKeyResponse(ApiKeyResponse):
    raw_key: str


class CreateKeyResponse(ApiKeyResponse):
    raw_key: str  # shown once only


@router.get("", response_model=List[ApiKeyResponse])
async def list_keys(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """List all API keys for this tenant."""
    keys = await list_api_keys(db, current_user.tenant_id)
    return [
        ApiKeyResponse(
            id=str(k.id), name=k.name, key_prefix=k.key_prefix,
            is_active=k.is_active, last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("", response_model=CreateKeyResponse, status_code=201)
async def create_key(
    data: CreateKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """
    Create a new API key.
    The raw key is returned once — store it securely. It cannot be retrieved again.
    """
    if not data.name.strip():
        raise HTTPException(400, "Key name is required")

    api_key, raw_key = await create_api_key(
        db=db,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        name=data.name.strip(),
    )
    return CreateKeyResponse(
        id=str(api_key.id), name=api_key.name, key_prefix=api_key.key_prefix,
        is_active=api_key.is_active, last_used_at=api_key.last_used_at,
        created_at=api_key.created_at, raw_key=raw_key,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """Revoke an API key. This cannot be undone."""
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(400, "Invalid key ID")

    revoked = await revoke_api_key(db, key_uuid, current_user.tenant_id)
    if not revoked:
        raise HTTPException(404, "API key not found")
