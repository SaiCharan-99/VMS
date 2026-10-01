from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from vms.api.deps import get_current_user, get_db
from vms.db.models import EvidenceItem, User
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
    user: User = Depends(get_current_user),
) -> FileResponse:
    item = db.get(EvidenceItem, evidence_id)
    if item is None or not storage.exists(item.storage_key):
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return FileResponse(storage.path(item.storage_key), media_type="image/jpeg")
