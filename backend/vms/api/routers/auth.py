from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from vms.api.deps import get_db, require_user
from vms.api.ratelimit import LoginLimiter
from vms.api.schemas import ChangePasswordIn, LoginIn, TokenOut, UserOut
from vms.config import get_settings
from vms.db.models import User
from vms.security import create_access_token
from vms.services import audit, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login", response_model=TokenOut, responses={429: {"description": "Too many failed logins"}}
)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    limiter: LoginLimiter = request.app.state.login_limiter
    email = users.normalize_email(body.email)
    ip = request.client.host if request.client else "unknown"
    if limiter.blocked(email, ip):
        raise HTTPException(status_code=429, detail="Too many failed logins. Try again later.")
    user = users.authenticate(db, email, body.password)
    if user is None:
        limiter.failed(email, ip)
        audit.log(db, "auth.login_failed", "user", None, {"email": email, "ip": ip})
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    limiter.reset(email, ip)
    audit.log(db, "auth.login", "user", user.id, {"ip": ip}, actor_user_id=user.id)
    db.commit()
    return TokenOut(
        access_token=create_access_token(user.id),
        expires_in=get_settings().jwt_ttl_hours * 3600,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(require_user)
) -> Response:
    try:
        users.change_password(db, user, body.current_password, body.new_password)
    except users.UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    db.commit()
    return Response(status_code=204)
