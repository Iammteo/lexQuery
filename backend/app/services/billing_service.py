"""
Billing service — Stripe integration and usage limit enforcement.

Plans and limits:
  trial        — 1 seat, 10k pages, 500 queries/month, 14 days
  starter      — 10 seats, 50k pages, 5k queries/month
  professional — 100 seats, 500k pages, 50k queries/month
  enterprise   — unlimited
"""
import uuid
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.tenant import Tenant

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Plan limits ───────────────────────────────────────────────────

PLAN_LIMITS = {
    "trial": {
        "seats": 1,
        "pages": 10_000,
        "queries_per_month": 500,
        "label": "Free Trial",
    },
    "starter": {
        "seats": 10,
        "pages": 50_000,
        "queries_per_month": 5_000,
        "label": "Starter",
    },
    "professional": {
        "seats": 100,
        "pages": 500_000,
        "queries_per_month": 50_000,
        "label": "Professional",
    },
    "enterprise": {
        "seats": 999_999,
        "pages": 999_999_999,
        "queries_per_month": 999_999_999,
        "label": "Enterprise",
    },
}


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])


def is_trial_expired(tenant: Tenant) -> bool:
    if not tenant.trial_ends_at:
        return False
    try:
        expires = datetime.fromisoformat(tenant.trial_ends_at)
        return datetime.now(timezone.utc) > expires
    except Exception:
        return False


def get_effective_plan(tenant: Tenant) -> str:
    """Return the effective plan, accounting for expired trials."""
    plan = tenant.current_plan or "trial"
    if plan == "trial" and is_trial_expired(tenant):
        return "expired"
    return plan


# ── Usage checks ──────────────────────────────────────────────────

async def check_query_limit(db: AsyncSession, tenant_id: uuid.UUID) -> Tuple[bool, str]:
    """
    Check if tenant can submit another query this month.
    Returns (allowed, error_message).
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()
    if not tenant:
        return False, "Tenant not found"

    plan = get_effective_plan(tenant)
    if plan == "expired":
        return False, "Your free trial has expired. Please upgrade to continue using LexQuery."

    limits = get_plan_limits(plan)
    monthly_limit = limits["queries_per_month"]

    # Reset counter if new month
    now = datetime.now(timezone.utc)
    if tenant.query_count_reset_at:
        try:
            reset_at = datetime.fromisoformat(tenant.query_count_reset_at)
            if now.month != reset_at.month or now.year != reset_at.year:
                tenant.query_count_this_month = 0
                tenant.query_count_reset_at = now.isoformat()
                await db.commit()
        except Exception:
            pass

    count = tenant.query_count_this_month or 0
    if count >= monthly_limit:
        return False, (
            f"You have reached your monthly query limit of {monthly_limit:,} on the "
            f"{limits['label']} plan. Upgrade to continue querying."
        )
    return True, ""


async def increment_query_count(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Increment the monthly query counter for a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()
    if not tenant:
        return
    now = datetime.now(timezone.utc)
    if not tenant.query_count_reset_at:
        tenant.query_count_reset_at = now.isoformat()
    tenant.query_count_this_month = (tenant.query_count_this_month or 0) + 1
    await db.commit()


async def check_document_limit(db: AsyncSession, tenant_id: uuid.UUID, new_pages: int = 0) -> Tuple[bool, str]:
    """Check if tenant can upload more documents."""
    from sqlalchemy import func
    from app.models.document import Document, DocumentStatus

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()
    if not tenant:
        return False, "Tenant not found"

    plan = get_effective_plan(tenant)
    if plan == "expired":
        return False, "Your free trial has expired. Please upgrade to continue uploading documents."

    limits = get_plan_limits(plan)
    page_limit = limits["pages"]

    # Count total indexed pages
    count_result = await db.execute(
        select(func.sum(Document.page_count)).where(
            Document.tenant_id == tenant_id,
            Document.status == DocumentStatus.INDEXED,
        )
    )
    total_pages = count_result.scalar() or 0

    if total_pages + new_pages > page_limit:
        return False, (
            f"Adding this document would exceed your page limit of {page_limit:,} on the "
            f"{limits['label']} plan. Upgrade to index more pages."
        )
    return True, ""


async def get_usage_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Return current usage vs limits for a tenant."""
    from sqlalchemy import func
    from app.models.document import Document, DocumentStatus
    from app.models.user import User

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()
    if not tenant:
        return {}

    plan = get_effective_plan(tenant)
    limits = get_plan_limits(plan if plan != "expired" else "trial")

    # Count pages
    pages_result = await db.execute(
        select(func.sum(Document.page_count)).where(
            Document.tenant_id == tenant_id,
            Document.status == DocumentStatus.INDEXED,
        )
    )
    total_pages = pages_result.scalar() or 0

    # Count seats
    seats_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id, User.is_active == True)
    )
    total_seats = seats_result.scalar() or 0

    trial_days_left = None
    if plan == "trial" and tenant.trial_ends_at:
        try:
            expires = datetime.fromisoformat(tenant.trial_ends_at)
            delta = expires - datetime.now(timezone.utc)
            trial_days_left = max(0, delta.days)
        except Exception:
            pass

    return {
        "plan": plan,
        "plan_label": limits["label"],
        "trial_days_left": trial_days_left,
        "subscription_status": tenant.subscription_status,
        "queries": {
            "used": tenant.query_count_this_month or 0,
            "limit": limits["queries_per_month"],
        },
        "pages": {
            "used": total_pages,
            "limit": limits["pages"],
        },
        "seats": {
            "used": total_seats,
            "limit": limits["seats"],
        },
    }


# ── Stripe ────────────────────────────────────────────────────────

def get_stripe():
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def create_checkout_session(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_email: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe checkout session and return the URL."""
    stripe = get_stripe()

    price_map = {
        "starter": settings.stripe_starter_price_id,
        "professional": settings.stripe_professional_price_id,
        "enterprise": settings.stripe_enterprise_price_id,
    }
    price_id = price_map.get(plan)
    if not price_id:
        raise ValueError(f"Unknown plan: {plan}")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()

    # Get or create Stripe customer
    customer_id = tenant.stripe_customer_id if tenant else None
    if not customer_id:
        customer = stripe.Customer.create(
            email=user_email,
            metadata={"tenant_id": str(tenant_id), "lexquery_plan": plan},
        )
        customer_id = customer.id
        if tenant:
            tenant.stripe_customer_id = customer_id
            await db.commit()

    trial_days = settings.stripe_trial_days if plan != "enterprise" else 0

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        subscription_data={"trial_period_days": trial_days} if trial_days else {},
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": str(tenant_id), "plan": plan},
    )
    return session.url


async def create_portal_session(db: AsyncSession, tenant_id: uuid.UUID, return_url: str) -> str:
    """Create a Stripe billing portal session and return the URL."""
    stripe = get_stripe()

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()

    if not tenant or not tenant.stripe_customer_id:
        raise ValueError("No Stripe customer found for this tenant")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


async def handle_webhook(db: AsyncSession, payload: bytes, sig_header: str) -> None:
    """Process a Stripe webhook event and update tenant accordingly."""
    stripe = get_stripe()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except Exception as e:
        raise ValueError(f"Invalid webhook signature: {e}")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"[stripe] Webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        tenant_id = data.get("metadata", {}).get("tenant_id")
        plan = data.get("metadata", {}).get("plan", "starter")
        subscription_id = data.get("subscription")
        if tenant_id:
            await _update_tenant_plan(db, uuid.UUID(tenant_id), plan, "active", subscription_id)

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status = data.get("status")
        plan = _plan_from_subscription(data)
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await _update_tenant_plan(db, uuid.UUID(tenant_id), plan, status, subscription_id)

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await _update_tenant_plan(db, uuid.UUID(tenant_id), "trial", "cancelled", None)

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            result = await db.execute(
                select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                tenant.subscription_status = "past_due"
                await db.commit()
                logger.warning(f"[stripe] Payment failed for tenant {tenant.id}")

    elif event_type == "customer.subscription.trial_will_end":
        tenant_id = data.get("metadata", {}).get("tenant_id")
        logger.info(f"[stripe] Trial ending soon for tenant {tenant_id}")


async def _update_tenant_plan(
    db: AsyncSession, tenant_id: uuid.UUID, plan: str, status: str, subscription_id: Optional[str]
) -> None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant: Optional[Tenant] = result.scalar_one_or_none()
    if not tenant:
        logger.error(f"[stripe] Tenant {tenant_id} not found")
        return
    tenant.current_plan = plan
    tenant.subscription_status = status
    if subscription_id:
        tenant.stripe_subscription_id = subscription_id
    await db.commit()
    logger.info(f"[stripe] Updated tenant {tenant_id} → plan={plan} status={status}")


def _plan_from_subscription(subscription: dict) -> str:
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return "starter"
    price_id = items[0].get("price", {}).get("id", "")
    s = get_settings()
    if price_id == s.stripe_professional_price_id:
        return "professional"
    if price_id == s.stripe_enterprise_price_id:
        return "enterprise"
    return "starter"
