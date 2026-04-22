from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.services.password_reset_service import (
    request_password_reset, validate_reset_token, reset_password
)

router = APIRouter()


class ResetRequestBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(data: ResetRequestBody, db: AsyncSession = Depends(get_db)):
    """Request a password reset email. Always returns 200 to prevent email enumeration."""
    try:
        await request_password_reset(db, str(data.email))
    except Exception:
        pass  # Silently fail — don't reveal errors
    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.get("/reset-password/validate")
async def validate_token(token: str):
    """Validate a reset token before showing the reset form."""
    data = validate_reset_token(token)
    if not data:
        raise HTTPException(400, "Invalid or expired reset link. Please request a new one.")
    return {"email": data["email"], "valid": True}


@router.post("/reset-password")
async def do_reset_password(data: ResetPasswordBody, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid token."""
    if len(data.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    success = await reset_password(db, data.token, data.new_password)
    if not success:
        raise HTTPException(400, "Invalid or expired reset link. Please request a new one.")
    return {"message": "Password reset successfully. You can now sign in."}
