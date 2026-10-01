from collections.abc import Callable, Iterator

from fastapi import Depends, HTTPException, Query, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from vms.db import get_sessionmaker
from vms.db.models import Role, User
from vms.security import decode_access_token, verify_media_signature
from vms.services import api_keys
from vms.services.principal import Principal

_bearer = HTTPBearer(auto_error=False)
_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)

ANY_ROLE = (Role.operator, Role.reviewer, Role.admin)
REVIEWER_UP = (Role.reviewer, Role.admin)


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_principal(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
    api_key: str | None = Security(_api_key),
) -> Principal:
    """`X-API-Key: <key>` or `Authorization: Bearer <jwt>`. Inactive users get 401."""
    if api_key:
        key = api_keys.verify(db, api_key)
        if key is None:
            raise _unauthorized("Invalid or revoked API key.")
        return Principal.for_api_key(key)
    if creds is None:
        raise _unauthorized("Not authenticated.")
    user_id = decode_access_token(creds.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token.")
    return Principal.for_user(user)


def require_role(*roles: Role) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Your role can't do this.")
        return principal

    return dependency


def require_user(principal: Principal = Depends(get_current_principal)) -> User:
    if principal.user is None:
        raise HTTPException(status_code=403, detail="This endpoint needs a user login.")
    return principal.user


def require_api_key(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.api_key is None:
        raise HTTPException(status_code=403, detail="This endpoint needs an API key.")
    return principal


def media_access(
    request: Request,
    exp: int | None = Query(None, description="Signed-URL expiry (unix s)"),
    sig: str | None = Query(None, description="Signed-URL signature"),
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
    api_key: str | None = Security(_api_key),
) -> Principal | None:
    """None when the URL carries a valid signature (it was issued to someone allowed to see it);
    otherwise the caller must authenticate normally."""
    if sig and verify_media_signature(request.url.path, exp, sig):
        return None
    return get_current_principal(db, creds, api_key)


any_role = require_role(*ANY_ROLE)
reviewer_up = require_role(*REVIEWER_UP)
admin_only = require_role(Role.admin)


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=200),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
