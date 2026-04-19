import uuid
import enum
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import TenantScopedMixin


class UserRole(str, enum.Enum):
    """
    Four roles in ascending order of privilege:

    VIEWER      — can query documents, read citations
    EDITOR      — viewer + can upload and ingest documents
    MATTER_ADMIN — editor + can manage workspace members and permissions
    TENANT_ADMIN — full control: users, billing, audit logs, config
    """

    VIEWER = "viewer"
    EDITOR = "editor"
    MATTER_ADMIN = "matter_admin"
    TENANT_ADMIN = "tenant_admin"


class User(Base, TenantScopedMixin):
    """
    A user belongs to exactly one tenant.
    Authentication is via JWT; the token carries tenant_id + role
    so every downstream service can enforce permissions without
    hitting the database on every request.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Null when SSO is the only auth method",
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
    String(50),
    nullable=False,
    default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # SSO — populated when user authenticates via SAML/OIDC
    sso_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sso_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
