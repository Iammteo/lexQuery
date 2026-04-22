import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.core.dependencies import get_current_user, CurrentUser

router = APIRouter()
logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    query_text: str
    citation_number: int
    document_id: str
    filename: str
    feedback: str  # 'up' or 'down'


@router.post("")
async def submit_feedback(
    data: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if data.feedback not in ("up", "down"):
        raise HTTPException(400, "feedback must be 'up' or 'down'")

    await db.execute(
        text("""
            INSERT INTO citation_feedback
                (id, tenant_id, user_id, document_id, query_text, citation_number, filename, feedback)
            VALUES
                (:id, :tenant_id, :user_id, :document_id, :query_text, :citation_number, :filename, :feedback)
        """),
        {
            "id": uuid.uuid4(),
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.user_id,
            "document_id": uuid.UUID(data.document_id),
            "query_text": data.query_text[:500],
            "citation_number": data.citation_number,
            "filename": data.filename,
            "feedback": data.feedback,
        }
    )
    await db.commit()
    logger.info(f"[feedback] {data.feedback} on citation {data.citation_number} from user {current_user.user_id}")
    return {"message": "Feedback recorded"}
