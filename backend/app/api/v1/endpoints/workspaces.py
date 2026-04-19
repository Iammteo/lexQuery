import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.workspace import Workspace
from app.core.dependencies import get_current_user, require_editor, CurrentUser
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all workspaces for the current tenant."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.tenant_id == current_user.tenant_id,
            Workspace.is_active.is_(True),
        )
    )
    workspaces = result.scalars().all()
    return [
        WorkspaceResponse(
            id=str(w.id),
            name=w.name,
            description=w.description,
            matter_number=w.matter_number,
            is_active=w.is_active,
            tenant_id=str(w.tenant_id),
        )
        for w in workspaces
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_editor),
):
    """Create a new workspace for the current tenant."""
    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=data.name,
        description=data.description,
        matter_number=data.matter_number,
        is_active=True,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        description=workspace.description,
        matter_number=workspace.matter_number,
        is_active=workspace.is_active,
        tenant_id=str(workspace.tenant_id),
    )
