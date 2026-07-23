"""add generation time tracking to documents

Revision ID: 0007_generation_time
Revises: 0006_password_reset
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_generation_time"
down_revision: Union[str, None] = "0006_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("generation_time_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "generation_time_seconds")
