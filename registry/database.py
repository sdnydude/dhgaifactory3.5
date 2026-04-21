"""
Shared database engine and session dependency.
This is the SOLE source of truth for database connections in the registry.
All endpoint files must import get_db and SessionLocal from here.
"""
import os

from prometheus_client import Gauge
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Prometheus gauge for active DB connections
db_connections = Gauge(
    'registry_db_connections',
    'Number of active database connections'
)


def get_database_url() -> str:
    """Get database URL with password from env or secret files."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    db_password_file = os.getenv("DB_PASSWORD_FILE", "/run/secrets/db_password")
    try:
        with open(db_password_file, "r") as f:
            password = f.read().strip()
    except FileNotFoundError:
        password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "weenie64")

    user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER", "dhg")
    host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "dhg_registry")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Database session dependency — Prometheus-tracked."""
    db = SessionLocal()
    db_connections.inc()
    try:
        yield db
    finally:
        db_connections.dec()
        db.close()
