from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vms.api.deps import any_role, get_db
from vms.api.schemas import JobOut
from vms.db.models import Job
from vms.services.principal import Principal

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(any_role),
) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not principal.can_see(job.video):
        raise HTTPException(status_code=403, detail="Not your job.")
    return JobOut.model_validate(job)
