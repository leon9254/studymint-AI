"""remove legacy active template ids

Revision ID: 0004_cleanup_templates
Revises: 0003_template_text_columns
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004_cleanup_templates"
down_revision: Union[str, None] = "0003_template_text_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CURRENT_TEMPLATE_ID = "exam_bundle_2026"
LEGACY_TEMPLATE_IDS = ("tpl_hesi_exit_exam_bundle_2026",)


def upgrade() -> None:
    for legacy_id in LEGACY_TEMPLATE_IDS:
        op.execute(
            f"UPDATE documents SET template_id = '{CURRENT_TEMPLATE_ID}' "
            f"WHERE template_id = '{legacy_id}'"
        )
        op.execute(f"DELETE FROM templates WHERE id = '{legacy_id}'")


def downgrade() -> None:
    # Data cleanup is intentionally not reversed.
    pass
