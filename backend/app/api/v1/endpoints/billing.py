import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.services.billing_service import (
    create_checkout_session, create_portal_session,
    handle_webhook, get_usage_summary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

FRONTEND_URL = "http://localhost:3000"


class CheckoutRequest(BaseModel):
    plan: str  # starter | professional | enterprise


@router.post("/create-checkout")
async def create_checkout(
    data: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a Stripe checkout session for a plan upgrade."""
    if data.plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(400, "Invalid plan")
    try:
        url = await create_checkout_session(
            db=db,
            tenant_id=current_user.tenant_id,
            user_email=current_user.email if hasattr(current_user, 'email') else "",
            plan=data.plan,
            success_url=f"{FRONTEND_URL}/billing/success?plan={data.plan}",
            cancel_url=f"{FRONTEND_URL}/billing/cancelled",
        )
        return {"url": url}
    except Exception as e:
        logger.error(f"[billing] Checkout failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/portal")
async def billing_portal(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Open the Stripe billing portal for subscription management."""
    try:
        url = await create_portal_session(
            db=db,
            tenant_id=current_user.tenant_id,
            return_url=f"{FRONTEND_URL}/dashboard/settings",
        )
        return {"url": url}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[billing] Portal failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/usage")
async def usage(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return current usage vs plan limits for the tenant."""
    return await get_usage_summary(db, current_user.tenant_id)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        await handle_webhook(db, payload, sig_header)
        return {"status": "ok"}
    except ValueError as e:
        logger.warning(f"[billing] Webhook rejected: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[billing] Webhook error: {e}")
        raise HTTPException(500, str(e))


@router.delete("/erase-all-data")
async def erase_all_data(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    GDPR right to erasure — permanently delete all tenant data.
    Requires Tenant Admin role. This cannot be undone.
    """
    from sqlalchemy import select, delete
    from app.models.user import User, UserRole
    from app.models.document import Document
    from app.models.workspace import Workspace, WorkspaceMember
    from app.models.audit_log import AuditLog
    from app.models.tenant import Tenant
    from app.services.s3_service import get_s3_service
    from app.services.weaviate_service import get_weaviate_service

    role = str(current_user.role).replace("UserRole.", "").strip()
    if role != "tenant_admin":
        raise HTTPException(403, "Only Tenant Admins can erase all data")

    tenant_id = current_user.tenant_id
    logger.warning(f"[gdpr] Erase all data requested for tenant {tenant_id}")

    # Delete documents from S3 and Weaviate
    try:
        docs_result = await db.execute(
            select(Document).where(Document.tenant_id == tenant_id)
        )
        docs = docs_result.scalars().all()
        s3 = get_s3_service()
        for doc in docs:
            try:
                s3.delete(doc.s3_key)
            except Exception:
                pass
        try:
            weaviate_svc = get_weaviate_service()
            for doc in docs:
                try:
                    weaviate_svc.delete_document_chunks(tenant_id, doc.id)
                except Exception:
                    pass
        except Exception:
            pass
    except Exception as e:
        logger.error(f"[gdpr] Storage cleanup failed: {e}")

    # Delete all DB records for this tenant
    try:
        await db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
        await db.execute(delete(Document).where(Document.tenant_id == tenant_id))
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.tenant_id == tenant_id))
        await db.execute(delete(Workspace).where(Workspace.tenant_id == tenant_id))
        await db.execute(delete(User).where(User.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"[gdpr] DB erasure failed: {e}")
        raise HTTPException(500, "Data erasure failed. Please contact support.")

    logger.warning(f"[gdpr] All data erased for tenant {tenant_id}")
    return {"message": "All data has been permanently deleted."}