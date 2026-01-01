"""Alembic environment configuration."""

import sys
from pathlib import Path
from logging.config import fileConfig

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from app.db.base import Base
# Import models to ensure they are registered with Base.metadata
from app.models import (
    user,
    student,
    trainer,
    session,
    attendance,
    notification,
    notification_preferences,
    facial_embedding,
    admin_message,
    smart_attendance,
    audit_log,
    webhook,
)

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/smartpresence"
)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url
    
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
