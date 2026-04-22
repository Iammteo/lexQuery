"""Sprint 5 — Citation feedback table

Revision ID: 005_sprint5
Revises: 004_sprint4
Create Date: 2025-04-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_sprint5"
down_revision: Union[str, None] = "004_sprint4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "citation_feedback",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("citation_number", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("feedback", sa.String(10), nullable=False),  # 'up' or 'down'
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("citation_feedback")
