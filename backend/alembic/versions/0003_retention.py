"""videos.disputed_at and videos.file_purged_at for retention

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("disputed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("file_purged_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.drop_column("file_purged_at")
        batch_op.drop_column("disputed_at")
