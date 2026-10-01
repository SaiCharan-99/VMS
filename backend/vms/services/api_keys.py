from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.db.models import ApiKey, utcnow
from vms.security import hash_api_key, new_api_key
from vms.services import audit
from vms.services.principal import Principal


def create(session: Session, name: str, actor: Principal) -> tuple[ApiKey, str]:
    """Returns the row and the plaintext key. Only the hash is stored; show the key once."""
    plaintext = new_api_key()
    key = ApiKey(name=name.strip(), key_hash=hash_api_key(plaintext), created_by=actor.user.id)
    session.add(key)
    session.flush()
    audit.log(session, "api_key.created", "api_key", key.id, {"name": key.name}, **actor.actor)
    return key, plaintext


def verify(session: Session, plaintext: str) -> ApiKey | None:
    """The active key matching `plaintext`, or None."""
    key = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(plaintext)))
    if key is None or key.revoked_at is not None:
        return None
    return key


def revoke(session: Session, key: ApiKey, actor: Principal) -> None:
    if key.revoked_at is None:
        key.revoked_at = utcnow()
        audit.log(session, "api_key.revoked", "api_key", key.id, {"name": key.name}, **actor.actor)
