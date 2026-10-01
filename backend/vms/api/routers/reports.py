from collections.abc import Iterator
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from vms.api.deps import get_db, reviewer_up
from vms.api.schemas import ReportSummary
from vms.db import get_sessionmaker
from vms.db.models import FinalStatus, ProcessType, Video, utcnow
from vms.services import reports
from vms.services import videos as video_svc
from vms.services.principal import Principal

router = APIRouter(prefix="/reports", tags=["reports"])

TzOffset = Query(0, ge=-720, le=840, description="Minutes east of UTC for day boundaries")


@router.get("/summary", response_model=ReportSummary)
def summary(
    date_from: date | None = Query(None, description="Local date; default 6 days before date_to"),
    date_to: date | None = Query(None, description="Local date, inclusive; default today"),
    group_by: reports.GroupBy = "day",
    process_type: ProcessType | None = None,
    station_id: int | None = None,
    tz_offset_min: int = TzOffset,
    db: Session = Depends(get_db),
    principal: Principal = Depends(reviewer_up),
) -> dict:
    """KPIs, grouped counts, and top failed checks for videos uploaded in the date range."""
    date_to = date_to or (utcnow() + timedelta(minutes=tz_offset_min)).date()
    date_from = date_from or date_to - timedelta(days=6)
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from is after date_to.")
    if (date_to - date_from).days > 366:
        raise HTTPException(status_code=400, detail="Date range is limited to one year.")
    start, end = reports.utc_bounds(date_from, date_to, tz_offset_min)
    stmt: Select = select(Video).where(
        Video.deleted_at.is_(None), Video.created_at >= start, Video.created_at < end
    )
    if process_type:
        stmt = stmt.where(Video.process_type == process_type)
    if station_id is not None:
        stmt = stmt.where(Video.station_id == station_id)
    rows = reports.load_rows(db, stmt, tz_offset_min)
    return reports.summarize(rows, date_from, date_to, group_by)


@router.get(
    "/export.csv",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/csv": {}}}},
)
def export_csv(
    status: FinalStatus | None = None,
    process_type: ProcessType | None = None,
    awb: str | None = None,
    q: str | None = None,
    station_id: int | None = None,
    uploaded_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = Query(None, description="Inclusive"),
    tz_offset_min: int = TzOffset,
    principal: Principal = Depends(reviewer_up),
) -> StreamingResponse:
    """Same filters as `GET /videos`. Streamed UTF-8 with a BOM so Excel opens it cleanly."""
    filters = video_svc.VideoFilters(status, process_type, awb, q, station_id, uploaded_by)
    stmt = video_svc.list_query(filters, principal, "created_at")
    if date_from or date_to:
        start, end = reports.utc_bounds(
            date_from or date(2000, 1, 1), date_to or date(9998, 12, 31), tz_offset_min
        )
        stmt = stmt.where(Video.created_at >= start, Video.created_at < end)

    def body() -> Iterator[str]:
        # Own session: the request's dependency session may close before streaming finishes.
        with get_sessionmaker()() as session:
            yield from reports.stream_csv(session, stmt, tz_offset_min)

    name = f"VMS_Audit_{utcnow():%Y%m%d_%H%M}.csv"
    return StreamingResponse(
        body(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
