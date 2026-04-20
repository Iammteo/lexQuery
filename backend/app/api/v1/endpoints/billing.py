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
