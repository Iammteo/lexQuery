import uuid
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import TenantScopedMixin


class Workspace(Base, TenantScopedMixin):
    """
    A Workspace is a container for documents within a tenant —
    think of it as a matter, a project, or a practice area.

    Example workspaces:
      - "Acme Corp Acquisition 2024"
      - "GDPR Compliance Docs"
      - "Employment Contracts"

    Users are granted access to workspaces via WorkspaceMember.
    All documents inside a workspace inherit the workspace's
    access controls.
    """

    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional matter reference (for law firm integrations)
    matter_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="External matter/case number from DMS",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="workspaces")
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace")
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name}>"


class WorkspaceMember(Base, TenantScopedMixin):
    """
    Junction table granting a user access to a workspace.
    A user can be a member of multiple workspaces within their tenant.
    """

    __tablename__ = "workspace_members"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    can_ingest: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if user can upload documents to this workspace",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id}>"
