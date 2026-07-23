"""add missing updated_at columns to log tables

Revision ID: 0002_add_missing_log_updated_at
Revises: 0001_initial
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_missing_log_updated_at"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in ("ai_usage_logs", "audit_logs")
    }

    if "updated_at" not in existing_columns["ai_usage_logs"]:
        op.add_column(
            "ai_usage_logs",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "updated_at" not in existing_columns["audit_logs"]:
        op.add_column(
            "audit_logs",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_column("audit_logs", "updated_at")
    op.drop_column("ai_usage_logs", "updated_at")
