# @TASK P0-T0.3 - Alembic environment: model registration and DB URL
# @SPEC docs/planning/04-database-design.md
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# Import every table model so SQLModel.metadata is fully populated before
# autogenerate inspects it.  The noqa comments suppress "imported but unused"
# lint warnings — these imports are intentional side-effects.
from app.models import (  # noqa: F401
    Alert,
    AlertRule,
    Cluster,
    Company,
    CompanyRelation,
    DataPoint,
    DataSource,
    NewsItem,
    User,
    UserFilter,
)

# Pull the database URL from the application settings so that any .env
# overrides (e.g. DATABASE_URL=postgresql://...) are respected automatically
# rather than relying solely on the static value in alembic.ini.
from app.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic config object — gives access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Override the sqlalchemy.url with the value from app settings so the
# migrations always target the same database the application uses.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging as declared in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — must be SQLModel.metadata so autogenerate works with
# SQLModel table models (which register themselves on this object).
# ---------------------------------------------------------------------------
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with only a URL (no live Engine/connection).
    Useful for generating SQL scripts without a running database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # render_as_batch=True is required for SQLite ALTER TABLE support.
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a live Engine and runs all pending migrations against it.
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
            # render_as_batch=True is required for SQLite ALTER TABLE support
            # (e.g. dropping columns, renaming columns, adding constraints).
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
