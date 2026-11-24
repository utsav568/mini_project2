"""
roadsafety/backend/database.py
==============================
SQLAlchemy database session management and engine configuration.
Supports PostgreSQL (with PostGIS) and SQLite WAL mode with automated seed data.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database URL from environment or default SQLite in WAL mode
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Use SQLite in WAL mode
    db_file = DATA_DIR / "roadsafety.db"
    DATABASE_URL = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration
    # Handle postgres:// -> postgresql:// for SQLAlchemy compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for database session injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
