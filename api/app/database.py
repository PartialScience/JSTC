"""
Database configuration and session management for JSTC API

This module provides database setup and session management.
Currently configured for SQLite but can be easily adapted for PostgreSQL, MySQL, etc.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from .core.config import get_settings

settings = get_settings()

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    # SQLite specific settings
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_database_session() -> Generator:
    """
    Get database session.
    
    This function provides a database session that automatically closes
    when the request is complete.
    
    Usage in FastAPI endpoints:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_database_session)):
            return crud.get_items(db, skip=0, limit=100)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    
    This function should be called on application startup to ensure
    all tables exist in the database.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    
    This function can be used for testing or during development
    to reset the database schema.
    """
    Base.metadata.drop_all(bind=engine)
