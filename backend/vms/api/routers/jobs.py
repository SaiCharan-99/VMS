from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vms.api.deps import get_current_user, get_db
from vms.api.schemas import JobOut
from vms.db.models import Job, User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobOut.model_validate(job)
