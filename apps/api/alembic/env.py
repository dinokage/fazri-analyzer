import os
import sys

# Make apps/api/ importable so `config`, `database`, and `models` can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Build the URL from app settings (avoids importing database.connection which
# creates a connection pool at import time with QueuePool/pool_size etc.)
from config import settings as _settings

_DATABASE_URL = (
    f"postgresql://{_settings.POSTGRES_USER}:{_settings.POSTGRES_PASSWORD}"
    f"@{_settings.POSTGRES_SERVER}:{_settings.POSTGRES_PORT}/{_settings.POSTGRES_DB}"
)

# Import Base so we have the shared metadata object
from database.connection import Base  # noqa: E402

# Import every model module so their tables register with Base.metadata.
# autogenerate compares Base.metadata against the live DB — any model not
# imported here will be invisible to Alembic and its table will be left out.
from models.db import alerts          # noqa: F401, E402
from models.db import camera_streams  # noqa: F401, E402
from models.db import webhooks        # noqa: F401, E402
from models.db import push_subscriptions  # noqa: F401, E402
from models.db import sensor_events   # noqa: F401, E402
from models.db import entity_profiles # noqa: F401, E402
from models.db import entity_identifiers  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the alembic.ini placeholder URL with the real database URL
config.set_main_option("sqlalchemy.url", _DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
