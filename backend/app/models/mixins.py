import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at and updated_at to every model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantScopedMixin(TimestampMixin):
    """
    Adds tenant_id to any model scoped to a tenant.
    Every table that inherits this is protected by Postgres
    Row-Level Security (RLS) — unauthorised tenants cannot
    read or write each other's rows even if they share the DB.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
