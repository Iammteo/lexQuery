import uuid
import csv
import io
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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
    """Retrieve audit logs for the current tenant. Requires Tenant Admin role."""
    workspace_uuid = None
    if workspace_id:
        try:
            workspace_uuid = uuid.UUID(workspace_id)
        except ValueError:
            raise HTTPException(400, "Invalid workspace_id")

    logs = await get_audit_logs(
        db=db, tenant_id=current_user.tenant_id,
        workspace_id=workspace_uuid, limit=limit, offset=offset,
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


@router.get("/export")
async def export_audit_logs(
    workspace_id: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """Export audit logs as CSV. Requires Tenant Admin role."""
    workspace_uuid = None
    if workspace_id:
        try:
            workspace_uuid = uuid.UUID(workspace_id)
        except ValueError:
            raise HTTPException(400, "Invalid workspace_id")

    logs = await get_audit_logs(
        db=db, tenant_id=current_user.tenant_id,
        workspace_id=workspace_uuid, limit=limit, offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "user_id", "query_text", "workspace_id",
        "confidence_score", "llm_model", "chunks_retrieved", "chunks_cited", "guardrail_flags"
    ])
    for log in logs:
        writer.writerow([
            str(log.id),
            log.created_at.isoformat(),
            str(log.user_id) if log.user_id else "",
            log.query_text,
            str(log.workspace_id) if log.workspace_id else "",
            log.confidence_score or "",
            log.llm_model or "",
            len(log.retrieved_doc_ids) if log.retrieved_doc_ids else 0,
            len(log.cited_doc_ids) if log.cited_doc_ids else 0,
            log.guardrail_flags or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )