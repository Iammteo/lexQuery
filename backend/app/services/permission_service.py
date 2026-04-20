"""
Document permission service.

Filters document access based on visibility settings.
Called before retrieval to build an allowed document ID list.
"""
import uuid
import json
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)

# async def get_allowed_document_ids(
#     db: AsyncSession,
#     tenant_id: uuid.UUID,
#     user_id: uuid.UUID,
#     user_role: str,
#     workspace_id: Optional[uuid.UUID] = None,
# ) -> Optional[List[uuid.UUID]]:
#     # Normalise role — strip enum prefix if present
#     role = str(user_role).replace("UserRole.", "").strip()

#     # Tenant admins bypass all restrictions
#     if role == "tenant_admin":
#         return None

async def get_allowed_document_ids(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_role: str,
    workspace_id: Optional[uuid.UUID] = None,
) -> Optional[List[uuid.UUID]]:
    # DEBUG — remove after fixing
    logger.info(f"[permissions] checking role='{user_role}' type={type(user_role)}")
    
    role = str(user_role).replace("UserRole.", "").strip()
    if role == "tenant_admin":
        return None
    
    # Fetch all indexed documents for this tenant/workspace
    query = select(Document).where(
        Document.tenant_id == tenant_id,
        Document.status == DocumentStatus.INDEXED,
    )
    if workspace_id:
        query = query.where(Document.workspace_id == workspace_id)

    result = await db.execute(query)
    documents = result.scalars().all()

    has_restrictions = any(d.visibility == "restricted" for d in documents)
    if not has_restrictions:
        return None

    allowed_ids = []
    for doc in documents:
        if doc.visibility != "restricted":
            allowed_ids.append(doc.id)
            continue

        allowed_roles = json.loads(doc.allowed_roles) if doc.allowed_roles else []
        allowed_user_ids = json.loads(doc.allowed_user_ids) if doc.allowed_user_ids else []

        role_allowed = role in allowed_roles
        user_allowed = str(user_id) in allowed_user_ids

        if role_allowed or user_allowed:
            allowed_ids.append(doc.id)
        else:
            logger.info(
                f"[permissions] Blocking doc {doc.id} ({doc.filename}) "
                f"from user {user_id} (role={role})"
            )

    return allowed_ids