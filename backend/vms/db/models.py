"""ORM models for the whole data model (IMPLEMENTATION.md §7).

Timestamps are naive UTC (`utcnow()`), so SQLite and Postgres compare them the same way.
"""

import enum
import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def new_uuid() -> str:
    return uuid_mod.uuid4().hex


class Base(DeclarativeBase):
    pass


def _enum(cls: type[enum.Enum]) -> Enum:
    # Stored as plain strings with a CHECK constraint, so Postgres needs no native enum types.
    return Enum(
        cls,
        native_enum=False,
        create_constraint=True,
        length=16,
        name=f"ck_{cls.__name__.lower()}",
        values_callable=lambda c: [m.value for m in c],
    )


class Role(enum.StrEnum):
    operator = "operator"
    reviewer = "reviewer"
    admin = "admin"


class ProcessType(enum.StrEnum):
    Forward = "Forward"
    Return = "Return"


class VideoSource(enum.StrEnum):
    web = "web"
    api = "api"
    legacy = "legacy"


class FinalStatus(enum.StrEnum):
    pending = "pending"
    pass_ = "pass"
    review = "review"
    fail = "fail"


class JobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class ReviewStatus(enum.StrEnum):
    pass_ = "pass"
    fail = "fail"


class Warehouse(Base):
    __tablename__ = "warehouses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (UniqueConstraint("warehouse_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role))
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        Index("ix_videos_awb", "awb"),
        Index("ix_videos_created_at", "created_at"),
        Index("ix_videos_final_status", "final_status"),
        Index("ix_videos_sha256", "sha256"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, default=new_uuid)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(255))  # None for legacy imports
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(100))
    process_type: Mapped[ProcessType] = mapped_column(_enum(ProcessType))
    awb: Mapped[str | None] = mapped_column(String(100))
    order_ref: Mapped[str | None] = mapped_column(String(100))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # Set for API-key uploads; an API key only sees the videos it uploaded.
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"), index=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id"))
    source: Mapped[VideoSource] = mapped_column(_enum(VideoSource))
    duration_s: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    final_status: Mapped[FinalStatus] = mapped_column(
        _enum(FinalStatus), default=FinalStatus.pending
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    # A disputed video is evidence in an open claim: retention never purges its file.
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Set when retention deleted the video file; the rows, analysis and evidence stay.
    file_purged_at: Mapped[datetime | None] = mapped_column(DateTime)

    jobs: Mapped[list["Job"]] = relationship(back_populates="video", order_by="Job.id")
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="video", order_by="Analysis.id"
    )
    reviews: Mapped[list["Review"]] = relationship(order_by="Review.id")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    status: Mapped[JobStatus] = mapped_column(_enum(JobStatus), default=JobStatus.queued)
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)

    video: Mapped[Video] = relationship(back_populates="jobs")


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, default=new_uuid)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))  # None for legacy imports
    schema_version: Mapped[str] = mapped_column(String(16))
    engine_version: Mapped[str] = mapped_column(String(32))
    rubric_id: Mapped[str] = mapped_column(String(64))
    total_score: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    decision: Mapped[str] = mapped_column(String(64))
    # Space-separated decoded barcode values, so `GET /videos?q=` can match any of them.
    barcodes: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    video: Mapped[Video] = relationship(back_populates="analyses")
    evidence: Mapped[list["EvidenceItem"]] = relationship(order_by="EvidenceItem.id")


class EvidenceItem(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    step_key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))
    t_s: Mapped[float] = mapped_column(Float)
    storage_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    final_status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus))
    reason_code: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"))
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
