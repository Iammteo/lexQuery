from fastapi import APIRouter

router = APIRouter()


@router.get("/logs")
async def get_audit_logs():
    """Retrieve audit log entries. (Step 7 — Audit logging)"""
    return {"message": "Not yet implemented — coming in Step 7"}
