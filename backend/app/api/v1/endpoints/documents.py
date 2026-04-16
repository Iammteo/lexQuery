from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def ingest_document():
    """Ingest a document into a workspace. (Step 4 — Ingestion pipeline)"""
    return {"message": "Not yet implemented — coming in Step 4"}


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Retrieve document metadata and index status."""
    return {"message": "Not yet implemented — coming in Step 4"}
