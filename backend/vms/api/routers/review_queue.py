from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vms.api.deps import PageParams, get_db, reviewer_up
from vms.api.schemas import Page, VideoOut
from vms.api.views import video_outs
from vms.db.models import ProcessType
from vms.services import reviews
from vms.services.principal import Principal

router = APIRouter(prefix="/review-queue", tags=["reviews"])


@router.get("", response_model=Page[VideoOut])
def review_queue(
    process_type: ProcessType | None = None,
    station_id: int | None = None,
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    principal: Principal = Depends(reviewer_up),
) -> Page[VideoOut]:
    """Videos whose final status is `review`, oldest first."""
    stmt = reviews.queue_query(process_type, station_id)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(paging.offset).limit(paging.page_size)).all()
    return Page[VideoOut](
        items=video_outs(db, rows), total=total or 0, page=paging.page, page_size=paging.page_size
    )
