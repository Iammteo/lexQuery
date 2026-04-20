"""Add source_url to documents for URL ingestion

Revision ID: 003_source_url
Revises: 002_email_verification_2fa
Create Date: 2025-04-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_source_url"
down_revision: Union[str, None] = "002_email_verification_2fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_url", sa.String(2000), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "source_url")
