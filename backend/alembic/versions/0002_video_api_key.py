"""videos.api_key_id for API-key upload isolation

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("api_key_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_videos_api_key_id", ["api_key_id"], unique=False)
        batch_op.create_foreign_key("fk_videos_api_key_id", "api_keys", ["api_key_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.drop_constraint("fk_videos_api_key_id", type_="foreignkey")
        batch_op.drop_index("ix_videos_api_key_id")
        batch_op.drop_column("api_key_id")
