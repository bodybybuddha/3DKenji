"""Database connection and session management."""

import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///./test.db"
)

# Create engine lazily on first use to handle dialect loading issues
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        logger.info(f"Creating engine with DATABASE_URL: {DATABASE_URL}")
        pool_class = NullPool if "sqlite" in DATABASE_URL else None
        _engine = create_engine(
            DATABASE_URL,
            poolclass=pool_class,
            echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Session:
    """Get database session (for dependency injection)."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

