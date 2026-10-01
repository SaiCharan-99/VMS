"""Admin CRUD: users, warehouses, stations, API keys, and the audit log."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from vms.api.deps import PageParams, admin_only, get_db
from vms.api.schemas import (
    ApiKeyCreated,
    ApiKeyIn,
    ApiKeyOut,
    AuditLogOut,
    Page,
    StationIn,
    StationOut,
    UserCreate,
    UserOut,
    UserUpdate,
    WarehouseIn,
    WarehouseOut,
)
from vms.db.models import ApiKey, AuditLog, Role, Station, User, Warehouse
from vms.services import api_keys, audit, users
from vms.services.principal import Principal

router = APIRouter(prefix="/admin", tags=["admin"])
Admin = Depends(admin_only)


def _page(db: Session, stmt: Select, paging: PageParams, out: type) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(paging.offset).limit(paging.page_size)).all()
    return {
        "items": [out.model_validate(r) for r in rows],
        "total": total or 0,
        "page": paging.page,
        "page_size": paging.page_size,
    }


def _user_error(exc: users.UserError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


# --- users -----------------------------------------------------------------------------------


@router.get("/users", response_model=Page[UserOut])
def list_users(
    role: Role | None = None,
    is_active: bool | None = None,
    warehouse_id: int | None = None,
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    admin: Principal = Admin,
) -> dict:
    stmt = select(User).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if warehouse_id is not None:
        stmt = stmt.where(User.warehouse_id == warehouse_id)
    return _page(db, stmt, paging, UserOut)


@router.post("/users", status_code=201, response_model=UserOut)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: Principal = Admin) -> User:
    try:
        user = users.create(db, **body.model_dump(), actor=admin)
    except users.UserError as exc:
        raise _user_error(exc) from exc
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, body: UserUpdate, db: Session = Depends(get_db), admin: Principal = Admin
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    fields = body.model_dump(exclude_unset=True)
    clear_warehouse = "warehouse_id" in fields and fields["warehouse_id"] is None
    try:
        users.update(db, user, admin, **fields, clear_warehouse=clear_warehouse)
    except users.UserError as exc:
        raise _user_error(exc) from exc
    db.commit()
    return user


# --- warehouses & stations -------------------------------------------------------------------


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), admin: Principal = Admin) -> list[Warehouse]:
    return list(db.scalars(select(Warehouse).order_by(Warehouse.code)))


@router.post("/warehouses", status_code=201, response_model=WarehouseOut)
def create_warehouse(
    body: WarehouseIn, db: Session = Depends(get_db), admin: Principal = Admin
) -> Warehouse:
    if db.scalar(select(Warehouse).where(Warehouse.code == body.code)):
        raise HTTPException(status_code=409, detail="Warehouse code already exists.")
    wh = Warehouse(code=body.code, name=body.name)
    db.add(wh)
    db.flush()
    audit.log(db, "warehouse.created", "warehouse", wh.id, body.model_dump(), **admin.actor)
    db.commit()
    return wh


@router.get("/stations", response_model=list[StationOut])
def list_stations(
    warehouse_id: int | None = None, db: Session = Depends(get_db), admin: Principal = Admin
) -> list[Station]:
    stmt = select(Station).order_by(Station.warehouse_id, Station.code)
    if warehouse_id is not None:
        stmt = stmt.where(Station.warehouse_id == warehouse_id)
    return list(db.scalars(stmt))


@router.post("/stations", status_code=201, response_model=StationOut)
def create_station(
    body: StationIn, db: Session = Depends(get_db), admin: Principal = Admin
) -> Station:
    if db.get(Warehouse, body.warehouse_id) is None:
        raise HTTPException(status_code=400, detail="Warehouse not found.")
    dup = select(Station).where(
        Station.warehouse_id == body.warehouse_id, Station.code == body.code
    )
    if db.scalar(dup):
        raise HTTPException(status_code=409, detail="Station code already exists here.")
    station = Station(**body.model_dump())
    db.add(station)
    db.flush()
    audit.log(db, "station.created", "station", station.id, body.model_dump(), **admin.actor)
    db.commit()
    return station


# --- API keys --------------------------------------------------------------------------------


@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(db: Session = Depends(get_db), admin: Principal = Admin) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).order_by(ApiKey.id)))


@router.post("/api-keys", status_code=201, response_model=ApiKeyCreated)
def create_api_key(
    body: ApiKeyIn, db: Session = Depends(get_db), admin: Principal = Admin
) -> ApiKeyCreated:
    key, plaintext = api_keys.create(db, body.name, admin)
    db.commit()
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=plaintext)


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: int, db: Session = Depends(get_db), admin: Principal = Admin
) -> Response:
    key = db.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    api_keys.revoke(db, key, admin)
    db.commit()
    return Response(status_code=204)


# --- audit log -------------------------------------------------------------------------------


@router.get("/audit-log", response_model=Page[AuditLogOut])
def list_audit_log(
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    actor_api_key_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    admin: Principal = Admin,
) -> dict:
    """Newest first. `action` matches a prefix, so `video.` returns every video action."""
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action, autoescape=True))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if actor_api_key_id is not None:
        stmt = stmt.where(AuditLog.actor_api_key_id == actor_api_key_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        end = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(AuditLog.created_at < end)
    return _page(db, stmt, paging, AuditLogOut)
