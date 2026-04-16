from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_workspaces():
    """List workspaces for current tenant. (Step 2 — DB schema)"""
    return {"message": "Not yet implemented — coming in Step 2"}


@router.post("")
async def create_workspace():
    """Create a workspace (matter/project). (Step 2 — DB schema)"""
    return {"message": "Not yet implemented — coming in Step 2"}
