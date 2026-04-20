"""Add email verification and 2FA fields to users

Revision ID: 002_email_verification_2fa
Revises: 001_initial_schema
Create Date: 2025-04-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_email_verification_2fa"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("verification_code", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("verification_code_expires", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("totp_secret", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "verification_code_expires")
    op.drop_column("users", "verification_code")
    op.drop_column("users", "email_verified")
