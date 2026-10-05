from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from tests.conftest import db_url_for, reset_db
from vms.db.models import Base, Role, User
from vms.db.session import SYSTEM_USER_EMAIL

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def test_alembic_upgrade_head_matches_models(tmp_path):
    url = db_url_for(tmp_path, "migrated.db")
    reset_db(url)
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert tables == set(Base.metadata.tables)
        video_cols = {c["name"] for c in inspect(engine).get_columns("videos")}
        assert "api_key_id" in video_cols  # 0002
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], diff  # the migrations build exactly what the models describe
        with Session(engine) as s:
            system = s.scalar(select(User).where(User.email == SYSTEM_USER_EMAIL))
            assert system is not None and system.role == Role.admin
        command.downgrade(cfg, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
