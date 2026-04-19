from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Document metadata returned to the client."""
    id: str
    filename: str
    document_type: str
    status: str
    chunk_count: Optional[int] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    workspace_id: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    """Lightweight document info for lists."""
    id: str
    filename: str
    status: str
    chunk_count: Optional[int] = None
    page_count: Optional[int] = None
    created_at: str
