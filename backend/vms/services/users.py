from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vms.db.models import Role, User, Warehouse, utcnow
from vms.security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from vms.services import audit
from vms.services.principal import Principal


class UserError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(422, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def _check_warehouse(session: Session, warehouse_id: int | None) -> None:
    if warehouse_id is not None and session.get(Warehouse, warehouse_id) is None:
        raise UserError(400, "Warehouse not found.")


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))


def create(
    session: Session,
    *,
    email: str,
    name: str,
    password: str,
    role: Role,
    warehouse_id: int | None = None,
    actor: Principal | None = None,
) -> User:
    _check_password(password)
    _check_warehouse(session, warehouse_id)
    if get_by_email(session, email) is not None:
        raise UserError(409, "A user with this email already exists.")
    user = User(
        email=normalize_email(email),
        name=name.strip(),
        password_hash=hash_password(password),
        role=role,
        warehouse_id=warehouse_id,
    )
    session.add(user)
    session.flush()
    audit.log(
        session,
        "user.created",
        "user",
        user.id,
        {"email": user.email, "role": role.value},
        **(actor.actor if actor else {}),
    )
    return user


def update(
    session: Session,
    user: User,
    actor: Principal,
    *,
    name: str | None = None,
    role: Role | None = None,
    warehouse_id: int | None = None,
    clear_warehouse: bool = False,
    is_active: bool | None = None,
    password: str | None = None,
) -> User:
    """Admin edit. An admin can't demote or deactivate themselves (avoids lock-out)."""
    is_self = actor.user is not None and actor.user.id == user.id
    if is_self and ((role is not None and role != Role.admin) or is_active is False):
        raise UserError(400, "You can't demote or deactivate your own account.")
    changes: dict[str, object] = {}
    if name is not None and name.strip() != user.name:
        user.name = changes["name"] = name.strip()
    if role is not None and role != user.role:
        user.role = role
        changes["role"] = role.value
    if clear_warehouse or warehouse_id is not None:
        _check_warehouse(session, warehouse_id)
        if warehouse_id != user.warehouse_id:
            user.warehouse_id = changes["warehouse_id"] = warehouse_id
    if is_active is not None and is_active != user.is_active:
        user.is_active = changes["is_active"] = is_active
    if password is not None:
        _check_password(password)
        user.password_hash = hash_password(password)
        changes["password"] = "reset"
    if changes:
        action = "user.deactivated" if changes.get("is_active") is False else "user.updated"
        audit.log(session, action, "user", user.id, changes, **actor.actor)
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    """The active user with these credentials, or None. Updates `last_login_at`."""
    user = get_by_email(session, email)
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        return None
    user.last_login_at = utcnow()
    return user


def change_password(session: Session, user: User, current: str, new: str) -> None:
    if not verify_password(user.password_hash, current):
        raise UserError(400, "Current password is incorrect.")
    _check_password(new)
    user.password_hash = hash_password(new)
    audit.log(session, "user.password_changed", "user", user.id, actor_user_id=user.id)
