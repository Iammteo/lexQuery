import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, Text, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AuditLog(Base):
    """
    Immutable record of every query submitted to LexQuery.

    Key design decisions:
    - No updated_at — audit logs are NEVER modified after creation
    - No cascade delete — logs must survive document/user deletion
    - tenant_id is stored directly (not FK) so logs persist even
      if a tenant is deleted (regulatory requirement)
    - Indexed on tenant_id + created_at for fast compliance exports

    Stores: who asked what, what was retrieved, what was cited,
    what confidence score was returned, and any guardrail flags triggered.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identity (stored as plain values, not FKs — survives user/tenant deletion)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp (UTC, millisecond precision)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # The query
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    # Retrieval results
    # List of document IDs retrieved before re-ranking (top-20)
    retrieved_doc_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # List of document IDs actually cited in the answer (top-5 after rerank)
    cited_doc_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Answer quality
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retrieval_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coverage_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # LLM metadata
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Guardrail flags (comma-separated list of triggered flags)
    guardrail_flags: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="e.g. 'low_confidence,legal_advice_disclaimer'",
    )

    # Answer hash (for tamper detection — plaintext stored separately in secure store)
    answer_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} tenant={self.tenant_id} "
            f"confidence={self.confidence_score}>"
        )
