import uuid
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus, DocumentType
from app.services.s3_service import get_s3_service
from app.services.document_parser import DocumentParser
from app.services.chunker import Chunker
from app.services.embedding_service import get_embedding_service
from app.services.weaviate_service import get_weaviate_service

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    pass


def run_ingestion_pipeline(db: Session, document_id: uuid.UUID) -> None:
    """
    Run the full ingestion pipeline for a single document.

    This function is called from the Celery worker. It uses a sync
    SQLAlchemy session because Celery workers don't run in an asyncio
    event loop.

    Pipeline:
      1. Load document metadata from Postgres
      2. Mark as PROCESSING
      3. Download raw file from S3
      4. Parse (PDF/DOCX → structured text with page numbers)
      5. Chunk (512-token windows with 128-token overlap)
      6. Embed (OpenAI text-embedding-3-large)
      7. Index into Weaviate (tenant-isolated namespace)
      8. Mark as INDEXED, record chunk count
    """
    logger.info(f"[ingest] Starting pipeline for document_id={document_id}")

    # Step 1 — load document metadata
    result = db.execute(select(Document).where(Document.id == document_id))
    doc: Optional[Document] = result.scalar_one_or_none()
    if not doc:
        raise IngestionError(f"Document {document_id} not found")

    try:
        # Step 2 — mark as processing
        doc.status = DocumentStatus.PROCESSING
        db.commit()
        logger.info(f"[ingest] doc={document_id} → PROCESSING")

        # Step 3 — download from S3
        s3 = get_s3_service()
        file_bytes = s3.download_to_bytes(doc.s3_key)
        logger.info(f"[ingest] doc={document_id} downloaded {len(file_bytes)} bytes")

        # Step 4 — parse
        parsed = DocumentParser.parse(
            file_bytes=file_bytes,
            document_type=DocumentType(doc.document_type),
        )
        logger.info(
            f"[ingest] doc={document_id} parsed {parsed.total_pages} pages, "
            f"{parsed.total_chars} chars"
        )

        # Update page count from the parser's actual result
        doc.page_count = parsed.total_pages
        db.commit()

        # Step 5 — chunk
        chunker = Chunker()
        chunks = chunker.chunk_document(parsed)
        logger.info(f"[ingest] doc={document_id} produced {len(chunks)} chunks")

        if not chunks:
            raise IngestionError("No chunks produced — document appears to be empty")

        # Step 6 — embed
        embed_svc = get_embedding_service()
        texts = [c.text for c in chunks]
        embeddings = embed_svc.embed_batch(texts)
        logger.info(
            f"[ingest] doc={document_id} generated {len(embeddings)} embeddings"
        )

        # Step 7 — index into Weaviate
        weaviate_svc = get_weaviate_service()
        indexed = weaviate_svc.index_chunks(
            tenant_id=doc.tenant_id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            filename=doc.filename,
            chunks=chunks,
            embeddings=embeddings,
            matter_number=doc.matter_number,
        )
        logger.info(f"[ingest] doc={document_id} indexed {indexed} chunks into Weaviate")

        # Step 8 — mark as indexed
        doc.status = DocumentStatus.INDEXED
        doc.chunk_count = indexed
        doc.error_message = None
        db.commit()
        logger.info(f"[ingest] doc={document_id} → INDEXED ({indexed} chunks)")

    except Exception as e:
        # Mark as failed so the user can see what happened
        logger.exception(f"[ingest] doc={document_id} FAILED: {e}")
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)[:2000]
        db.commit()
        raise
