"""
Alembic migration environment for InvIQ.

Key integrations:
  - Imports Base from app.infrastructure.database.connection so Alembic
    can auto-detect schema changes from the SQLAlchemy models.
  - Reads DATABASE_URL from the app's Settings (which loads from .env)
    so there is a single source of truth — no duplicate config in alembic.ini.
  - Supports both online (live DB) and offline (SQL script) migration modes.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Load application config so DATABASE_URL comes from .env via pydantic-settings
# ---------------------------------------------------------------------------

import sys
import os

# Make sure the backend package is importable when running alembic from
# the backend/ directory (e.g.  alembic upgrade head)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings  # noqa: E402
from app.infrastructure.database.connection import Base  # noqa: E402

# Import ALL models here so Alembic can see them for auto-generation.
# If you add a new model, import its module below.
import app.infrastructure.database.models  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Alembic config object (gives access to values in alembic.ini)
# ---------------------------------------------------------------------------

config = context.config

# Override sqlalchemy.url with the value from pydantic-settings
# so we don't have to duplicate the connection string in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — required for --autogenerate
# ---------------------------------------------------------------------------

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration (generates SQL script without a live connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (applies changes to a live database)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
