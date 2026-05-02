import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
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

EXTENSION_MAP = {
    "pdf": (DocumentType.PDF, "application/pdf"),
    "docx": (DocumentType.DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "txt": (DocumentType.TXT, "text/plain"),
}

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all documents for the current tenant, optionally filtered by workspace."""
    query = select(Document).where(Document.tenant_id == current_user.tenant_id)
    if workspace_id:
        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            raise HTTPException(400, "Invalid workspace_id")
        query = query.where(Document.workspace_id == ws_uuid)
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=str(d.id), filename=d.filename, document_type=d.document_type,
            status=d.status, chunk_count=d.chunk_count, page_count=d.page_count,
            file_size_bytes=d.file_size_bytes, workspace_id=str(d.workspace_id),
            error_message=d.error_message,
        )
        for d in docs
    ]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    matter_number: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_editor),
):
    """Upload a document into a workspace."""
    if not file.filename:
        raise HTTPException(400, "Filename required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in EXTENSION_MAP:
        raise HTTPException(400, f"Unsupported file type '.{ext}'. Supported: {', '.join(EXTENSION_MAP.keys())}")
    document_type, content_type = EXTENSION_MAP[ext]

    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(400, "Invalid workspace_id")

    workspace_result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_uuid, Workspace.tenant_id == current_user.tenant_id)
    )
    workspace = workspace_result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(413, f"File too large. Max size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB")
    if file_size == 0:
        raise HTTPException(400, "File is empty")

    document = Document(
        id=uuid.uuid4(), tenant_id=current_user.tenant_id, workspace_id=workspace.id,
        uploaded_by=current_user.user_id, filename=file.filename, document_type=document_type,
        file_size_bytes=file_size, s3_key="", status=DocumentStatus.PENDING, matter_number=matter_number,
    )

    s3 = get_s3_service()
    s3_key = s3.build_key(current_user.tenant_id, document.id, file.filename)

    import io
    try:
        s3.upload_fileobj(file_obj=io.BytesIO(file_bytes), key=s3_key, content_type=content_type)
    except Exception as e:
        raise HTTPException(500, f"S3 upload failed: {e}")

    document.s3_key = s3_key
    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        ingest_document.delay(str(document.id))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to enqueue ingestion: {e}")

    return DocumentResponse(
        id=str(document.id), filename=document.filename, document_type=document.document_type,
        status=document.status, chunk_count=document.chunk_count, page_count=document.page_count,
        file_size_bytes=document.file_size_bytes, workspace_id=str(document.workspace_id),
        error_message=document.error_message,
    )


@router.post("/from-url", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_url(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_editor),
):
    """Fetch a public URL and ingest it as a document."""
    import logging
    logger = logging.getLogger(__name__)

    url = data.get("url", "").strip()
    workspace_id = data.get("workspace_id", "").strip()

    if not url:
        raise HTTPException(400, "url is required")
    if not workspace_id:
        raise HTTPException(400, "workspace_id is required")

    try:
        ws_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(400, "Invalid workspace_id")

    workspace_result = await db.execute(
        select(Workspace).where(Workspace.id == ws_uuid, Workspace.tenant_id == current_user.tenant_id)
    )
    if not workspace_result.scalar_one_or_none():
        raise HTTPException(404, "Workspace not found")

    try:
        from app.services.url_fetcher import fetch_url, extract_text_from_html, URLFetchError
        file_bytes, detected_type, title = fetch_url(url)
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch URL: {e}")

    if detected_type == "html":
        text = extract_text_from_html(file_bytes, url)
        if not text or len(text.strip()) < 50:
            raise HTTPException(400, "Could not extract meaningful text from this URL.")
        file_bytes = text.encode("utf-8")
        detected_type = "txt"

    ext_map = {"pdf": DocumentType.PDF, "docx": DocumentType.DOCX, "txt": DocumentType.TXT}
    doc_type = ext_map.get(detected_type, DocumentType.TXT)

    safe_title = title[:200].replace("/", "_").replace("\\", "_") + f".{detected_type}"

    document = Document(
        id=uuid.uuid4(), tenant_id=current_user.tenant_id, workspace_id=ws_uuid,
        uploaded_by=current_user.user_id, filename=safe_title, document_type=doc_type,
        file_size_bytes=len(file_bytes), s3_key="", status=DocumentStatus.PENDING,
    )

    s3 = get_s3_service()
    s3_key = s3.build_key(current_user.tenant_id, document.id, safe_title)

    import io
    try:
        content_type_map = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain"}
        s3.upload_fileobj(file_obj=io.BytesIO(file_bytes), key=s3_key, content_type=content_type_map.get(detected_type, "text/plain"))
    except Exception as e:
        raise HTTPException(500, f"S3 upload failed: {e}")

    document.s3_key = s3_key
    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        ingest_document.delay(str(document.id))
    except Exception as e:
        logger.warning(f"Failed to enqueue ingestion for URL doc: {e}")

    return DocumentResponse(
        id=str(document.id), filename=document.filename, document_type=document.document_type,
        status=document.status, chunk_count=document.chunk_count, page_count=document.page_count,
        file_size_bytes=document.file_size_bytes, workspace_id=str(document.workspace_id),
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
        select(Document).where(Document.id == doc_uuid, Document.tenant_id == current_user.tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    return DocumentResponse(
        id=str(doc.id), filename=doc.filename, document_type=doc.document_type,
        status=doc.status, chunk_count=doc.chunk_count, page_count=doc.page_count,
        file_size_bytes=doc.file_size_bytes, workspace_id=str(doc.workspace_id),
        error_message=doc.error_message,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_editor),
):
    """Delete a document and remove it from S3 and Weaviate."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document_id")

    result = await db.execute(
        select(Document).where(Document.id == doc_uuid, Document.tenant_id == current_user.tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    try:
        s3 = get_s3_service()
        s3.delete(doc.s3_key)
    except Exception:
        pass

    try:
        from app.services.weaviate_service import get_weaviate_service
        weaviate_svc = get_weaviate_service()
        weaviate_svc.delete_document_chunks(current_user.tenant_id, doc_uuid)
    except Exception:
        pass

    await db.delete(doc)
    await db.commit()


@router.get("/{document_id}/view")
async def view_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a presigned URL or content for viewing a document inline."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document_id")

    result = await db.execute(
        select(Document).where(Document.id == doc_uuid, Document.tenant_id == current_user.tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    doc_type = str(doc.document_type).replace("DocumentType.", "").lower()

    if doc_type == "txt":
        try:
            s3 = get_s3_service()
            file_bytes = s3.download_to_bytes(doc.s3_key)
            content = file_bytes.decode("utf-8", errors="replace")
            return {"url": None, "filename": doc.filename, "document_type": doc_type, "content": content}
        except Exception as e:
            raise HTTPException(500, f"Failed to retrieve document: {e}")
    else:
        try:
            s3 = get_s3_service()
            url = s3.generate_presigned_url(doc.s3_key, expires_in=3600)
            return {"url": url, "filename": doc.filename, "document_type": doc_type}
        except Exception as e:
            raise HTTPException(500, f"Failed to generate view URL: {e}")


@router.patch("/{document_id}/permissions")
async def update_permissions(
    document_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update document visibility and access permissions."""
    import json
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document_id")

    result = await db.execute(
        select(Document).where(Document.id == doc_uuid, Document.tenant_id == current_user.tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    role = str(current_user.role).replace("UserRole.", "").strip()
    if role not in ("tenant_admin", "matter_admin"):
        raise HTTPException(403, "Insufficient permissions to update document access")

    if "visibility" in data:
        doc.visibility = data["visibility"]
    if "allowed_roles" in data:
        doc.allowed_roles = json.dumps(data["allowed_roles"]) if isinstance(data["allowed_roles"], list) else data["allowed_roles"]
    if "allowed_user_ids" in data:
        doc.allowed_user_ids = json.dumps(data["allowed_user_ids"]) if isinstance(data["allowed_user_ids"], list) else data["allowed_user_ids"]

    await db.commit()
    return {"message": "Permissions updated"}