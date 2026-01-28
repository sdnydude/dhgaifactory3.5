"""
Shared database session dependency
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Database setup - use environment variables
DB_HOST = os.getenv("POSTGRES_HOST", "dhg-registry-db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "dhg")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "changeme")
DB_NAME = os.getenv("POSTGRES_DB", "dhg_registry")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
