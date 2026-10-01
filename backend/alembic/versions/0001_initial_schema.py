"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-01 17:05:50.200459
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "code"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "operator",
                "reviewer",
                "admin",
                name="ck_role",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column(
            "process_type",
            sa.Enum(
                "Forward",
                "Return",
                name="ck_processtype",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("awb", sa.String(length=100), nullable=True),
        sa.Column("order_ref", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("station_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "web",
                "api",
                "legacy",
                name="ck_videosource",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "final_status",
            sa.Enum(
                "pending",
                "pass",
                "review",
                "fail",
                name="ck_finalstatus",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.create_index("ix_videos_awb", ["awb"], unique=False)
        batch_op.create_index("ix_videos_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_videos_final_status", ["final_status"], unique=False)
        batch_op.create_index("ix_videos_sha256", ["sha256"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_api_key_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_api_key_id"],
            ["api_keys.id"],
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_audit_log_created_at"), ["created_at"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "done",
                "failed",
                name="ck_jobstatus",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.create_index("ix_jobs_status", ["status"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=32), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("rubric_id", sa.String(length=64), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("barcodes", sa.Text(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    with op.batch_alter_table("analyses", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_analyses_video_id"), ["video_id"], unique=False)

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("t_s", sa.Float(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_evidence_analysis_id"), ["analysis_id"], unique=False)

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column(
            "final_status",
            sa.Enum(
                "pass",
                "fail",
                name="ck_reviewstatus",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_reviews_video_id"), ["video_id"], unique=False)

    # Built-in admin that stubbed auth acts as until Phase 3 (vms.db.session.SYSTEM_USER_EMAIL).
    users = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("name", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        users,
        [
            {
                "email": "system@vms.local",
                "name": "System",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.now(UTC).replace(tzinfo=None),
            }
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reviews_video_id"))

    op.drop_table("reviews")
    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_evidence_analysis_id"))

    op.drop_table("evidence")
    with op.batch_alter_table("analyses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_analyses_video_id"))

    op.drop_table("analyses")
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_jobs_status")

    op.drop_table("jobs")
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_log_created_at"))

    op.drop_table("audit_log")
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.drop_index("ix_videos_sha256")
        batch_op.drop_index("ix_videos_final_status")
        batch_op.drop_index("ix_videos_created_at")
        batch_op.drop_index("ix_videos_awb")

    op.drop_table("videos")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("stations")
    op.drop_table("warehouses")
