"""Response models for /api/v1. Datetimes are UTC and serialized with a trailing `Z`."""

from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

from vms.analysis.result import AnalysisResult
from vms.db.models import FinalStatus, JobStatus, ProcessType, ReviewStatus, Role, VideoSource

UtcDateTime = Annotated[
    datetime, PlainSerializer(lambda d: d.isoformat(timespec="seconds") + "Z", return_type=str)
]
T = TypeVar("T")


class _Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class UserOut(_Orm):
    id: int
    email: str
    name: str
    role: Role


class JobOut(_Orm):
    id: int
    video_id: int
    status: JobStatus
    progress: float
    attempts: int
    max_attempts: int
    error: str | None
    created_at: UtcDateTime
    started_at: UtcDateTime | None
    finished_at: UtcDateTime | None


class AnalysisBrief(_Orm):
    id: int
    uuid: str
    schema_version: str
    rubric_id: str
    total_score: int
    confidence: float
    status: str
    decision: str
    created_at: UtcDateTime


class EvidenceOut(_Orm):
    id: int
    step_key: str
    kind: str
    t_s: float
    url: str


class AnalysisOut(AnalysisBrief):
    engine_version: str
    job_id: int | None
    # Schema 2.0 for engine results; legacy imports keep their schema 1.0 dict.
    result: AnalysisResult | dict[str, Any]
    evidence: list[EvidenceOut]


class VideoOut(_Orm):
    id: int
    uuid: str
    original_filename: str
    size_bytes: int | None
    content_type: str | None
    process_type: ProcessType
    awb: str | None
    order_ref: str | None
    uploaded_by: int | None
    station_id: int | None
    source: VideoSource
    duration_s: float | None
    created_at: UtcDateTime
    final_status: FinalStatus
    stream_url: str | None = None
    latest_analysis: AnalysisBrief | None = None


class ReviewOut(_Orm):
    id: int
    analysis_id: int
    reviewer_id: int
    final_status: ReviewStatus
    reason_code: str
    comment: str | None
    created_at: UtcDateTime


class VideoDetail(BaseModel):
    video: VideoOut
    analysis: AnalysisOut | None
    reviews: list[ReviewOut]
    job: JobOut | None


class UploadOut(BaseModel):
    video: VideoOut
    job: JobOut | None
    duplicate: bool


class HealthOut(BaseModel):
    status: str
    version: str
    db: str
    detectors: dict[str, bool]


class RubricStepOut(BaseModel):
    key: str
    title: str
    description: str
    weight: int


class RubricOut(BaseModel):
    id: str
    process_type: ProcessType
    title: str
    steps: list[RubricStepOut]
