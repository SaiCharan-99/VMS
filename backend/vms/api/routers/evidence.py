from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from vms.api.deps import any_role, get_db
from vms.db.models import Analysis, EvidenceItem
from vms.services.principal import Principal
from vms.storage import Storage, get_storage

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get(
    "/{evidence_id}",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    principal: Principal = Depends(any_role),
) -> FileResponse:
    item = db.get(EvidenceItem, evidence_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    if not principal.can_see(db.get(Analysis, item.analysis_id).video):
        raise HTTPException(status_code=403, detail="Not your evidence.")
    if not storage.exists(item.storage_key):
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return FileResponse(storage.path(item.storage_key), media_type="image/jpeg")
