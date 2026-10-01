from collections.abc import Iterator

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from vms.db import get_sessionmaker, seed
from vms.db.models import User


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def get_current_user(db: Session = Depends(get_db)) -> User:
    """Phase 2 stub: every request acts as the built-in system admin. Phase 3 adds JWT/API keys."""
    user = seed(db)
    db.commit()
    return user


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
