"""Response models for /api/v1. Datetimes are UTC and serialized with a trailing `Z`."""

from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

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
    warehouse_id: int | None
    is_active: bool
    created_at: UtcDateTime
    last_login_at: UtcDateTime | None


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(max_length=256)
    role: Role
    warehouse_id: int | None = None


class UserUpdate(BaseModel):
    """Only the fields sent are changed. `warehouse_id: null` clears it; `password` resets it."""

    name: str | None = Field(None, min_length=1, max_length=200)
    role: Role | None = None
    warehouse_id: int | None = None
    is_active: bool | None = None
    password: str | None = Field(None, max_length=256)


class WarehouseIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)


class WarehouseOut(_Orm):
    id: int
    code: str
    name: str
    created_at: UtcDateTime


class StationIn(BaseModel):
    warehouse_id: int
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)


class StationOut(_Orm):
    id: int
    warehouse_id: int
    code: str
    name: str


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ApiKeyOut(_Orm):
    id: int
    name: str
    created_by: int
    created_at: UtcDateTime
    revoked_at: UtcDateTime | None


class ApiKeyCreated(ApiKeyOut):
    key: str = Field(description="The plaintext key. Shown only once; store it now.")


class AuditLogOut(_Orm):
    id: int
    actor_user_id: int | None
    actor_api_key_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    data: dict[str, Any] | None
    created_at: UtcDateTime


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
