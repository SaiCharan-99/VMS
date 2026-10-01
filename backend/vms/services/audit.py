from typing import Any

from sqlalchemy.orm import Session

from vms.db.models import AuditLog


def log(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    data: dict[str, Any] | None = None,
    *,
    actor_user_id: int | None = None,
    actor_api_key_id: int | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            actor_api_key_id=actor_api_key_id,
            action=action,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            data=data,
        )
    )
