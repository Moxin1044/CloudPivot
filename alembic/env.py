from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base
from app.config import settings

# Import all models so Alembic can detect them
from app.models import *  # noqa

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    """Convert async DATABASE_URL to synchronous driver for Alembic."""
    url = settings.DATABASE_URL
    return url.replace("+asyncpg", "+psycopg2").replace("+asyncmy", "+pymysql")


def run_migrations_offline() -> None:
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sync_url = _get_sync_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
