from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lexquery",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.ingest_document": {"queue": "ingestion"},
    },
    worker_prefetch_multiplier=1,  # one task at a time per worker (ingestion is heavy)
    task_acks_late=True,           # ack only after completion — no lost tasks on crash
)
