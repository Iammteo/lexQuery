import uuid
import enum
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import TenantScopedMixin


class DocumentStatus(str, enum.Enum):
    """
    Lifecycle of a document through the ingestion pipeline.

    PENDING     — uploaded to S3, queued for processing
    PROCESSING  — Celery worker is actively parsing/chunking/embedding
    INDEXED     — fully indexed in Weaviate, available for retrieval
    FAILED      — pipeline error, see error_message for details
    """

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    MD = "markdown"
    HTML = "html"


class Document(Base, TenantScopedMixin):
    """
    Tracks every document uploaded to LexQuery.

    The actual file lives in S3 at s3://{bucket}/{tenant_id}/{id}/{filename}.
    The vector chunks live in Weaviate under the tenant's namespace.
    This table is the metadata record linking everything together.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
    String(50), nullable=False
)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # S3 location
    s3_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Full S3 key: {tenant_id}/{doc_id}/{filename}",
    )

    # Ingestion state
    status: Mapped[DocumentStatus] = mapped_column(
    String(50),
    nullable=False,
    default=DocumentStatus.PENDING,
    index=True,
)
    chunk_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of chunks indexed in Weaviate",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Populated if status=failed",
    )

    # Legal metadata (extracted during ingestion)
    matter_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    document_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Date extracted from document content",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"
