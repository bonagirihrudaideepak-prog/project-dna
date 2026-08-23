from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import settings
from ..models.base import Base

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist (safe for dev; production uses Alembic migrations).

    Importing the model package is required: ``Base.metadata`` only knows about
    modules that have been imported. Without this, a standalone call (scripts,
    tests, CI) would silently create an empty subset of tables.
    """
    from .. import models  # noqa: F401 - registers all ORM classes on Base.metadata

    Base.metadata.create_all(bind=engine, checkfirst=True)