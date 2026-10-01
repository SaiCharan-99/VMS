from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from vms.db.models import Base, Role, User
from vms.db.session import SYSTEM_USER_EMAIL

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def test_alembic_upgrade_head_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert tables == set(Base.metadata.tables)
        with Session(engine) as s:
            system = s.scalar(select(User).where(User.email == SYSTEM_USER_EMAIL))
            assert system is not None and system.role == Role.admin
        command.downgrade(cfg, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
