"""expand template style text columns

Revision ID: 0003_template_text_columns
Revises: 0002_add_missing_log_updated_at
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_template_text_columns"
down_revision: Union[str, None] = "0002_add_missing_log_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("templates", "description", existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=False)
    op.alter_column("templates", "cover_style", existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=False)
    op.alter_column("templates", "section_style", existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("templates", "section_style", existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=False)
    op.alter_column("templates", "cover_style", existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=False)
    op.alter_column("templates", "description", existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=False)
