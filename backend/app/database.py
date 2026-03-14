"""
DiaIntel — Database Connection
SQLAlchemy engine, session factory, and base model.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings


# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """Dependency that provides a database session.

    Usage in FastAPI routes:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables.

    Note: In production, tables are created by init.sql via Docker.
    This is a fallback for development.
    """
    Base.metadata.create_all(bind=engine)
