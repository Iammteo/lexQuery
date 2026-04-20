"""
User management endpoints — Tenant Admin only.

GET  /v1/users                    → list all users in tenant
PATCH /v1/users/{id}/role         → change a user's role
PATCH /v1/users/{id}/deactivate   → deactivate a user
PATCH /v1/users/{id}/activate     → reactivate a user
POST /v1/users/invite             → invite a new user by email
POST /v1/users/accept-invite      → accept invite and set password
GET  /v1/users/invite/{token}     → get invite info (email, role, tenant)
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import require_tenant_admin, get_current_user, CurrentUser
from app.services.auth_service import create_invite, accept_invite, _invites, AuthError
from app.schemas.auth import TokenResponse

router = APIRouter()


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool


class ChangeRoleRequest(BaseModel):
    role: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str
    password: str


class InviteInfoResponse(BaseModel):
    email: str
    role: str
    tenant_name: str


@router.get("", response_model=List[UserListItem])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """List all users in the current tenant."""
    result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id).order_by(User.created_at)
    )
    users = result.scalars().all()
    return [
        UserListItem(
            id=str(u.id), email=u.email, full_name=u.full_name,
            role=u.role, is_active=u.is_active, email_verified=u.email_verified,
        )
        for u in users
    ]


@router.patch("/{user_id}/role")
async def change_role(
    user_id: str,
    data: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """Change a user's role. Cannot change your own role."""
    if user_id == str(current_user.user_id):
        raise HTTPException(400, "You cannot change your own role")

    valid_roles = [r.value for r in UserRole]
    if data.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.role = data.role
    await db.commit()
    return {"message": f"Role updated to {data.role}"}


@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    if user_id == str(current_user.user_id):
        raise HTTPException(400, "You cannot deactivate your own account")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = False
    await db.commit()
    return {"message": "User deactivated"}


@router.patch("/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = True
    await db.commit()
    return {"message": "User reactivated"}


@router.post("/invite")
async def invite_user(
    data: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_tenant_admin),
):
    """Invite a new user to the organisation by email."""
    valid_roles = [r.value for r in UserRole]
    if data.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    try:
        token = await create_invite(
            db=db,
            tenant_id=current_user.tenant_id,
            invited_by_user_id=current_user.user_id,
            invitee_email=str(data.email),
            role=data.role,
        )
    except AuthError as e:
        raise HTTPException(e.status_code, e.message)
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"message": f"Invitation sent to {data.email}", "token": token}


@router.get("/invite/{token}", response_model=InviteInfoResponse)
async def get_invite_info(token: str, db: AsyncSession = Depends(get_db)):
    """Get invite details so the accept page can pre-fill the email."""
    from datetime import datetime, timezone
    invite = _invites.get(token)
    if not invite:
        raise HTTPException(404, "Invalid or expired invitation link")

    expires = datetime.fromisoformat(invite["expires"])
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(400, "This invitation has expired")

    from sqlalchemy import select as sa_select
    from app.models.tenant import Tenant
    tenant_result = await db.execute(sa_select(Tenant).where(Tenant.id == uuid.UUID(invite["tenant_id"])))
    tenant = tenant_result.scalar_one_or_none()

    return InviteInfoResponse(
        email=invite["email"],
        role=invite["role"],
        tenant_name=tenant.name if tenant else "your organisation",
    )


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite_endpoint(
    data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invite and create an account."""
    try:
        return await accept_invite(db, data.token, data.full_name, data.password)
    except AuthError as e:
        raise HTTPException(e.status_code, e.message)
