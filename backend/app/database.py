"""Database connection.

Locally this is a SQLite file (backend/dispensers.db) that needs no setup.
On Render, DATABASE_URL points at a Postgres database instead.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config

_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Give each request its own database session and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
