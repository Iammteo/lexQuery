import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.core.config import get_settings
from app.schemas.query import QueryRequest, QueryResponse
from app.services.retrieval_service import get_retrieval_service
from app.services.answer_service import generate_answer
from app.services.audit_service import write_audit_log

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("", response_model=QueryResponse)
async def submit_query(
    data: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Submit a natural language query against indexed documents.

    Flow:
      1. Parse workspace scope (optional)
      2. Run hybrid retrieval (vector + BM25 + RRF + rerank)
      3. Generate answer with LLM using retrieved passages
      4. Write immutable audit log
      5. Return answer + citations + confidence score
    """
    if not data.query or not data.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    workspace_uuid: Optional[uuid.UUID] = None
    if data.workspace_id:
        try:
            workspace_uuid = uuid.UUID(data.workspace_id)
        except ValueError:
            raise HTTPException(400, "Invalid workspace_id")

    logger.info(
        f"[query] user={current_user.user_id} "
        f"tenant={current_user.tenant_id} "
        f"query='{data.query[:60]}'"
    )

    try:
        # Step 1 — retrieve relevant chunks
        retrieval_svc = get_retrieval_service()
        chunks = retrieval_svc.retrieve(
            tenant_id=current_user.tenant_id,
            query=data.query,
            workspace_id=workspace_uuid,
            top_k=data.top_k,
            top_n=data.top_n,
        )

        # Step 2 — generate answer with citations
        answer, citations, confidence_score, confidence_label = generate_answer(
            query=data.query,
            chunks=chunks,
        )

        # Step 3 — write audit log
        retrieved_doc_ids = list({c.document_id for c in chunks})
        cited_doc_ids = [c.document_id for c in citations]

        try:
            await write_audit_log(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.user_id,
                query_text=data.query,
                workspace_id=workspace_uuid,
                retrieved_doc_ids=retrieved_doc_ids,
                cited_doc_ids=cited_doc_ids,
                confidence_score=confidence_score,
                retrieval_confidence=confidence_score,
                answer_text=answer,
                llm_model=settings.llm_model,
            )
        except Exception as audit_err:
            # Never fail a query because of an audit logging error
            logger.error(f"[audit] Failed to write audit log: {audit_err}")

        return QueryResponse(
            query=data.query,
            answer=answer,
            citations=citations,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
            chunks_retrieved=len(chunks),
            chunks_used=len(citations),
            workspace_id=data.workspace_id,
        )

    except Exception as e:
        logger.exception(f"[query] Failed: {e}")
        raise HTTPException(500, f"Query failed: {str(e)}")