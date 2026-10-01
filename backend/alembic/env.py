from logging.config import fileConfig

from alembic import context
from vms.config import get_settings
from vms.db.models import Base
from vms.db.session import make_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


def _url() -> str:
    # sqlalchemy.url is only set by tests; normally the URL comes from VMS_DB_URL.
    return config.get_main_option("sqlalchemy.url") or get_settings().db_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=Base.metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
