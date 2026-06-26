"""
Shared database session dependency
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    _db_pw = os.getenv("POSTGRES_PASSWORD")
    if not _db_pw:
        raise RuntimeError(
            "Database not configured: set DATABASE_URL or POSTGRES_PASSWORD"
        )
    DATABASE_URL = f"postgresql://dhg:{_db_pw}@172.20.0.14:5432/dhg_registry"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
