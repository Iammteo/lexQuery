import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.workspace import Workspace
from app.core.dependencies import get_current_user, require_editor, CurrentUser
from app.services.s3_service import get_s3_service
from app.workers.tasks import ingest_document
from app.schemas.document import DocumentResponse

router = APIRouter()

# Map file extensions to document types + MIME types we accept
EXTENSION_MAP = {
    "pdf": (DocumentType.PDF, "application/pdf"),
    "docx": (DocumentType.DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "txt": (DocumentType.TXT, "text/plain"),
}

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    matter_number: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_editor),
):
    """
    Upload a document into a workspace.

    Flow:
      1. Validate file type and size
      2. Verify the workspace belongs to the user's tenant
      3. Upload to S3 under the tenant's prefix
      4. Create Document row in Postgres (status=PENDING)
      5. Enqueue Celery task for background processing
      6. Return immediately — client polls for status
    """

    # Validate file extension
    if not file.filename:
        raise HTTPException(400, "Filename required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in EXTENSION_MAP:
        raise HTTPException(
            400,
            f"Unsupported file type '.{ext}'. Supported: {', '.join(EXTENSION_MAP.keys())}",
        )
    document_type, content_type = EXTENSION_MAP[ext]

    # Validate workspace belongs to this tenant
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(400, "Invalid workspace_id")

    workspace_result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_uuid,
            Workspace.tenant_id == current_user.tenant_id,
        )
    )
    workspace = workspace_result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    # Read file into memory & check size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            413,
            f"File too large. Max size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
        )
    if file_size == 0:
        raise HTTPException(400, "File is empty")

    # Create Document row first so we have an ID for the S3 key
    document = Document(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        workspace_id=workspace.id,
        uploaded_by=current_user.user_id,
        filename=file.filename,
        document_type=document_type,
        file_size_bytes=file_size,
        s3_key="",  # filled in next
        status=DocumentStatus.PENDING,
        matter_number=matter_number,
    )

    s3 = get_s3_service()
    s3_key = s3.build_key(current_user.tenant_id, document.id, file.filename)

    # Upload to S3
    import io
    try:
        s3.upload_fileobj(
            file_obj=io.BytesIO(file_bytes),
            key=s3_key,
            content_type=content_type,
        )
    except Exception as e:
        raise HTTPException(500, f"S3 upload failed: {e}")

    # Save document row
    document.s3_key = s3_key
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Enqueue background ingestion
    try:
        ingest_document.delay(str(document.id))
    except Exception as e:
        # If Celery broker is down, still return 201 — worker will pick it up later
        # or the user can manually retry. We log but don't fail the upload.
        import logging
        logging.getLogger(__name__).warning(f"Failed to enqueue ingestion: {e}")

    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        document_type=document.document_type,
        status=document.status,
        chunk_count=document.chunk_count,
        page_count=document.page_count,
        file_size_bytes=document.file_size_bytes,
        workspace_id=str(document.workspace_id),
        error_message=document.error_message,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve document metadata and current ingestion status."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document_id")

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        document_type=doc.document_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        file_size_bytes=doc.file_size_bytes,
        workspace_id=str(doc.workspace_id),
        error_message=doc.error_message,
    )
