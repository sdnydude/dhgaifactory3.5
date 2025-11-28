from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os

# Import models for autogenerate support
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

# Get database URL from environment
def get_url():
    db_password_file = os.getenv("DB_PASSWORD_FILE", "/run/secrets/db_password")
    try:
        with open(db_password_file, 'r') as f:
            password = f.read().strip()
    except FileNotFoundError:
        # Fallback for local development
        password = os.getenv("DB_PASSWORD", "dhg_password")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://dhg_user@registry-db:5432/dhg_registry")
    # Insert password into URL
    if "@" in db_url:
        protocol, rest = db_url.split("://", 1)
        user_host = rest.split("@", 1)
        if len(user_host) == 2:
            user, host = user_host
            db_url = f"{protocol}://{user}:{password}@{host}"
    
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
