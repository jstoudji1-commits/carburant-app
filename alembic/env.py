import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from optiplein_db import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url():

    url = os.getenv("DATABASE_URL", "").strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def migrations_postgres_disponibles():

    url = database_url()
    return bool(
        url.startswith("postgresql+psycopg://")
        or url.startswith("postgresql://")
        or url.startswith("postgres://")
    )


def run_migrations_offline():

    url = database_url()
    if not migrations_postgres_disponibles():
        print("DATABASE_URL non configuree, migration Alembic ignoree.")
        return

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():

    if not migrations_postgres_disponibles():
        print("DATABASE_URL non configuree, migration Alembic ignoree.")
        return

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url()

    connectable = engine_from_config(
        configuration,
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
