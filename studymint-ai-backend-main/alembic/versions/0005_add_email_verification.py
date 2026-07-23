"""add user email verification fields

Revision ID: 0005_email_verification
Revises: 0004_cleanup_templates
Create Date: 2026-07-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_email_verification"
down_revision: Union[str, None] = "0004_cleanup_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_users_email_verification_token_hash",
        "users",
        ["email_verification_token_hash"],
        unique=False,
    )
    op.execute("UPDATE users SET email_verified = true WHERE email_verified = false")


def downgrade() -> None:
    op.drop_index("ix_users_email_verification_token_hash", table_name="users")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
