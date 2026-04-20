"""Sprint 4 — Stripe billing, API keys, document permissions

Revision ID: 004_sprint4
Revises: 003_source_url
Create Date: 2025-04-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_sprint4"
down_revision: Union[str, None] = "003_source_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Stripe + billing fields on tenants ──────────────────────
    op.add_column("tenants", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("stripe_subscription_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("subscription_status", sa.String(50), nullable=True, server_default="trialing"))
    op.add_column("tenants", sa.Column("current_plan", sa.String(50), nullable=True, server_default="trial"))
    op.add_column("tenants", sa.Column("trial_ends_at", sa.String(50), nullable=True))
    op.add_column("tenants", sa.Column("query_count_this_month", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("tenants", sa.Column("query_count_reset_at", sa.String(50), nullable=True))
    op.add_column("tenants", sa.Column("logo_url", sa.String(500), nullable=True))

    # ── Document permissions ─────────────────────────────────────
    op.add_column("documents", sa.Column("visibility", sa.String(20), nullable=True, server_default="all"))
    op.add_column("documents", sa.Column("allowed_roles", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("allowed_user_ids", sa.Text(), nullable=True))

    # ── API keys table ───────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(200), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    for col in ["visibility", "allowed_roles", "allowed_user_ids"]:
        op.drop_column("documents", col)
    for col in ["stripe_customer_id", "stripe_subscription_id", "subscription_status",
                "current_plan", "trial_ends_at", "query_count_this_month",
                "query_count_reset_at", "logo_url"]:
        op.drop_column("tenants", col)
