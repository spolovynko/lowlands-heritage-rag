import logging
import os

from alembic import context
from sqlalchemy import URL, create_engine, pool

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5.5s [%(name)s] %(message)s",
)

target_metadata = None


def required_environment_variable(name: str) -> str:
    """Return a required non-empty environment variable."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} must be set to a non-empty value.")
    return value


def database_url() -> URL:
    """Build the PostgreSQL connection URL from environment variables."""
    port_value = os.environ.get("POSTGRES_PORT", "5432")

    try:
        port = int(port_value)
    except ValueError as error:
        raise RuntimeError("POSTGRES_PORT must be an integer.") from error

    return URL.create(
        drivername="postgresql+psycopg",
        username=required_environment_variable("POSTGRES_USER"),
        password=required_environment_variable("POSTGRES_PASSWORD"),
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=port,
        database=required_environment_variable("POSTGRES_DB"),
    )


def run_migrations_offline() -> None:
    """Generate migration SQL without opening a database connection."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    connectable = create_engine(database_url(), poolclass=pool.NullPool)

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
