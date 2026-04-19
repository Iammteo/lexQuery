from typing import Optional
from pydantic import BaseModel


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    matter_number: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    matter_number: Optional[str] = None
    is_active: bool
    tenant_id: str

    class Config:
        from_attributes = True
