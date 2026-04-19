import uuid
import hashlib
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def write_audit_log(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    query_text: str,
    workspace_id: Optional[uuid.UUID],
    retrieved_doc_ids: List[str],
    cited_doc_ids: List[str],
    confidence_score: float,
    retrieval_confidence: float,
    answer_text: str,
    llm_model: str,
    guardrail_flags: Optional[str] = None,
    session_id: Optional[str] = None,
) -> AuditLog:
    answer_hash = hashlib.sha256(answer_text.encode()).hexdigest()

    log = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        query_text=query_text,
        workspace_id=workspace_id,
        retrieved_doc_ids=[str(d) for d in retrieved_doc_ids],
        cited_doc_ids=[str(d) for d in cited_doc_ids],
        confidence_score=confidence_score,
        retrieval_confidence=retrieval_confidence,
        coverage_confidence=None,
        llm_model=llm_model,
        guardrail_flags=guardrail_flags,
        answer_hash=answer_hash,
    )

    db.add(log)
    await db.commit()

    logger.info(
        f"[audit] tenant={tenant_id} user={user_id} "
        f"confidence={confidence_score} cited={len(cited_doc_ids)} docs"
    )

    return log


async def get_audit_logs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[AuditLog]:
    query = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if workspace_id:
        query = query.where(AuditLog.workspace_id == workspace_id)

    result = await db.execute(query)
    return list(result.scalars().all())