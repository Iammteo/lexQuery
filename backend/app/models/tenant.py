import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Text , Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import TimestampMixin

class Tenant(Base, TimestampMixin):
    """
    A Tenant is a single organisation using LexQuery —
    a law firm, an in-house legal team, or an API consumer.

    Every other table in the system is scoped to a tenant_id.
    Tenants are fully isolated — no data crosses tenant boundaries.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe identifier e.g. 'acme-legal'",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Subscription tier — controls feature access and limits
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="starter",
        comment="starter | professional | enterprise",
    )

    # Data residency — determines which AWS region data is stored in
    data_region: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="eu-west-2",
        comment="eu-west-2 | eu-west-1 | us-east-1",
    )

    # Optional: tenant-level config overrides (JSON blob)
    config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON: custom LLM model, retention policy, etc.",
    )

    # Stripe billing
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subscription_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="trialing")
    current_plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="trial")
    trial_ends_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    query_count_this_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    query_count_reset_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships (populated as other models are added)
    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug} plan={self.plan}>"
