from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """
    Creates a new tenant and its first Tenant Admin user in one step.
    This is the onboarding flow — one request, one organisation set up.
    """
    # Tenant details
    tenant_name: str
    tenant_slug: str  # e.g. "acme-legal" — must be URL-safe

    # First admin user
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("tenant_slug")
    @classmethod
    def slug_must_be_url_safe(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers and hyphens")
        return v

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned on successful login or registration."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: str
    tenant_id: str
    role: str


class UserResponse(BaseModel):
    """Public user profile — never includes hashed_password."""
    id: str
    email: str
    full_name: Optional[str]
    role: str
    tenant_id: str
    is_active: bool

    class Config:
        from_attributes = True
