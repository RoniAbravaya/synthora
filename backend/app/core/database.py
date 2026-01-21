"""
Synthora Database Configuration

This module sets up the SQLAlchemy database connection, session management,
and provides the base model class for all database models.

Features:
- Async-ready SQLAlchemy configuration
- Session dependency for FastAPI
- Base model with common fields
- Connection pooling configuration
"""

from datetime import datetime
from typing import Generator
import uuid

from sqlalchemy import create_engine, Column, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings


# Get settings
settings = get_settings()

# Create SQLAlchemy engine with connection pooling
# For production, these values should be tuned based on expected load
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,  # Number of connections to keep open
    max_overflow=10,  # Additional connections allowed beyond pool_size
    pool_timeout=30,  # Seconds to wait for a connection from pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG and settings.is_development,  # Log SQL in development
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    All models should inherit from this class to get:
    - Automatic table name generation
    - Common timestamp fields
    - UUID primary key support
    
    Example:
        class User(Base):
            __tablename__ = "users"
            
            id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            email = Column(String, unique=True, nullable=False)
    """
    pass


class TimestampMixin:
    """
    Mixin class that adds created_at and updated_at timestamp fields.
    
    Usage:
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            # ... other fields
    """
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when the record was created"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class UUIDMixin:
    """
    Mixin class that adds a UUID primary key.
    
    Usage:
        class User(Base, UUIDMixin, TimestampMixin):
            __tablename__ = "users"
            # ... other fields (no need to define id)
    """
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the record"
    )


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.
    
    This is used as a FastAPI dependency to inject database sessions
    into route handlers. The session is automatically closed after
    the request completes.
    
    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function should be called during application startup
    to ensure all tables exist. In production, use Alembic
    migrations instead.
    
    Note: This imports all models to ensure they're registered
    with SQLAlchemy before creating tables.
    """
    # Import all models here to register them with SQLAlchemy
    # This ensures all tables are created
    from app.models import (  # noqa: F401
        user,
        subscription,
        integration,
        template,
        video,
        social_account,
        post,
        analytics,
        ai_suggestion,
        notification,
        job,
        app_settings,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


def enable_pgcrypto(db: Session) -> None:
    """
    Enable the pgcrypto extension in PostgreSQL.
    
    This extension provides cryptographic functions for
    database-level encryption.
    
    Args:
        db: Database session
    """
    db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    db.commit()


def check_database_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


def get_database_info() -> dict:
    """
    Get information about the database connection.
    
    Returns:
        dict: Database information including version and connection status
    """
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT version()"))
        version = result.scalar()
        db.close()
        return {
            "connected": True,
            "version": version,
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }

