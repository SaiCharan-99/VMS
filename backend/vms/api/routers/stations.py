from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.api.deps import any_role, get_db
from vms.api.schemas import StationOut
from vms.db.models import Station
from vms.services.principal import Principal

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationOut])
def list_stations(
    db: Session = Depends(get_db),
    principal: Principal = Depends(any_role),
) -> list[StationOut]:
    """All stations, for the upload form's station picker (management stays under /admin)."""
    rows = db.scalars(select(Station).order_by(Station.warehouse_id, Station.code))
    return [StationOut.model_validate(s) for s in rows]
