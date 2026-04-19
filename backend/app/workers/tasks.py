import uuid
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.workers.celery_app import celery_app
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Celery workers run outside asyncio — use a sync engine
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
_SyncSession = sessionmaker(_sync_engine, expire_on_commit=False)


@celery_app.task(name="app.workers.tasks.ingest_document", bind=True, max_retries=2)
def ingest_document(self, document_id: str):
    """
    Celery task — runs the ingestion pipeline asynchronously.
    The API returns immediately after uploading to S3;
    this worker does the heavy parsing/embedding/indexing.
    """
    from app.services.ingestion_service import run_ingestion_pipeline

    session = _SyncSession()
    try:
        run_ingestion_pipeline(session, uuid.UUID(document_id))
    except Exception as exc:
        logger.exception(f"Ingestion failed for document {document_id}")
        # Retry with backoff — 60s, then 180s
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        session.close()
