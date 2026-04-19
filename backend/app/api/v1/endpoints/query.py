from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def submit_query():
    """Submit a natural language query. (Step 6 — Answer generation)"""
    return {"message": "Not yet implemented — coming in Step 6"}
