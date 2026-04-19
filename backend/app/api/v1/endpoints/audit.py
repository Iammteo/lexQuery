import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import require_tenant_admin, CurrentUser
from app.services.audit_service import get_audit_logs

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    query_text: str
    workspace_id: Optional[str]
    retrieved_doc_ids: Optional[list]
    cited_doc_ids: Optional[list]
    confidence_score: Optional[float]
    llm_model: Optional[str]
    guardrail_flags: Optional[str]
    created_at: str


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_log_entries(
    workspace_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """
    Retrieve audit logs for the current tenant.
    Requires Tenant Admin role.
    """
    workspace_uuid = None
    if workspace_id:
        try:
            workspace_uuid = uuid.UUID(workspace_id)
        except ValueError:
            raise HTTPException(400, "Invalid workspace_id")

    logs = await get_audit_logs(
        db=db,
        tenant_id=current_user.tenant_id,
        workspace_id=workspace_uuid,
        limit=limit,
        offset=offset,
    )

    return [
        AuditLogResponse(
            id=str(log.id),
            user_id=str(log.user_id) if log.user_id else None,
            query_text=log.query_text,
            workspace_id=str(log.workspace_id) if log.workspace_id else None,
            retrieved_doc_ids=log.retrieved_doc_ids,
            cited_doc_ids=log.cited_doc_ids,
            confidence_score=log.confidence_score,
            llm_model=log.llm_model,
            guardrail_flags=log.guardrail_flags,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]