"""Engine and session factory built from `settings.db_url`."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from vms.config import get_settings
from vms.db.models import Base, Role, User

SYSTEM_USER_EMAIL = "system@vms.local"


def make_engine(url: str) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)

    db_file = url.removeprefix("sqlite:///")
    if db_file and db_file != ":memory:":
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:  # noqa: ANN001
        cur = dbapi_conn.cursor()
        # WAL lets the API read while a worker writes; busy_timeout covers short write locks.
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().db_url)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session that commits on success and rolls back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def seed(session: Session) -> User:
    """Ensure the built-in `system` user exists. It has no password, so it can't log in;
    it only marks system-written records."""
    user = session.scalar(select(User).where(User.email == SYSTEM_USER_EMAIL))
    if user is None:
        user = User(email=SYSTEM_USER_EMAIL, name="System", role=Role.admin)
        session.add(user)
        session.flush()
    return user


def create_all(engine: Engine | None = None) -> None:
    """Create tables directly (tests and throwaway DBs); real DBs use `alembic upgrade head`."""
    engine = engine or get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        session.commit()
