import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine

from vms import security
from vms.analysis.detectors import get_ocr_reader, get_yolo
from vms.config import Settings, get_settings
from vms.db import create_all, get_engine, get_sessionmaker, session_scope
from vms.db.models import Role, User
from vms.services import api_keys, users
from vms.services.principal import Principal

TEST_PASSWORD = "correct-horse-1"
# CI's Postgres leg sets this; each test then starts from an empty schema in that database.
PG_TEST_URL = os.environ.get("VMS_TEST_DB_URL")


def db_url_for(tmp_path: Path, name: str = "vms.db") -> str:
    return PG_TEST_URL or f"sqlite:///{(tmp_path / name).as_posix()}"


def reset_db(url: str) -> None:
    """Drop every table (and the alembic stamp) so a shared Postgres DB starts empty."""
    engine = create_engine(url)
    try:
        meta = MetaData()
        meta.reflect(engine)
        meta.drop_all(engine)
    finally:
        engine.dispose()


def _clear_caches() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()  # release the SQLite file so tmp_path can be removed
    get_settings.cache_clear()
    get_ocr_reader.cache_clear()
    get_yolo.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    security.jwt_secret.cache_clear()


@pytest.fixture(autouse=True)
def isolated_settings(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Keep tests off the real DB/data dir; disable heavy models unless marked `models`."""
    # A developer's `.env` must not leak into tests (e.g. VMS_JWT_SECRET defeats the prod check).
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("VMS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VMS_DB_URL", db_url_for(tmp_path))
    monkeypatch.setenv("VMS_ENV", "dev")
    monkeypatch.setenv("VMS_JWT_SECRET", "test-secret-" + "x" * 32)
    # Cheap argon2 parameters keep the role matrix fast; production uses the library defaults.
    monkeypatch.setattr(security, "_hasher", PasswordHasher(time_cost=1, memory_cost=1024))
    if request.node.get_closest_marker("models") is None:
        monkeypatch.setenv("VMS_OCR_ENABLED", "false")
        monkeypatch.setenv("VMS_YOLO_ENABLED", "false")
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def db_ready() -> None:
    """Tables + seeded system user in the per-test DB."""
    if PG_TEST_URL:
        reset_db(PG_TEST_URL)
    create_all()


@pytest.fixture
def make_user(db_ready: None) -> Callable[..., User]:
    """`make_user(Role.operator)` -> a committed user with password `TEST_PASSWORD`."""
    counter = iter(range(1, 10_000))

    def make(role: Role = Role.operator, email: str | None = None, **kw) -> User:
        email = email or f"{role.value}{next(counter)}@test.local"
        with session_scope() as s:
            return users.create(
                s, email=email, name=email.split("@")[0], password=TEST_PASSWORD, role=role, **kw
            )

    return make


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user.id)}"}


@pytest.fixture
def make_api_key(make_user: Callable[..., User]) -> Callable[[], tuple[int, dict[str, str]]]:
    """`make_api_key()` -> (key id, headers)."""

    def make() -> tuple[int, dict[str, str]]:
        admin = make_user(Role.admin)
        with session_scope() as s:
            key, plaintext = api_keys.create(s, "test key", Principal.for_user(s.merge(admin)))
            return key.id, {"X-API-Key": plaintext}

    return make


@pytest.fixture
def app(db_ready: None) -> FastAPI:
    from vms.api.main import create_app

    return create_app()


@pytest.fixture
def anon_client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(app: FastAPI, make_user: Callable[..., User]) -> Iterator[TestClient]:
    """Logged in as an admin (sees and may do everything)."""
    with TestClient(app, headers=auth(make_user(Role.admin, "admin@test.local"))) as c:
        yield c
