import uuid
import enum
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import TenantScopedMixin


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    MATTER_ADMIN = "matter_admin"
    TENANT_ADMIN = "tenant_admin"


class User(Base, TenantScopedMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(String(50), nullable=False, default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    verification_code_expires: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # TOTP / 2FA
    totp_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # SSO
    sso_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sso_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"