from fastapi import APIRouter, Depends

from vms.analysis.rubric import DEFAULT_RUBRICS, get_rubric
from vms.api.deps import get_current_user
from vms.api.schemas import RubricOut, RubricStepOut
from vms.db.models import User

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("", response_model=list[RubricOut])
def list_rubrics(user: User = Depends(get_current_user)) -> list[RubricOut]:
    """Active rubrics, one per process type (step titles and descriptions for the UI)."""
    out = []
    for rubric_id in DEFAULT_RUBRICS.values():
        r = get_rubric(rubric_id)
        steps = [
            RubricStepOut(key=s.key, title=s.title, description=s.description, weight=s.weight)
            for s in r.steps
        ]
        out.append(RubricOut(id=r.id, process_type=r.process_type, title=r.title, steps=steps))
    return out
