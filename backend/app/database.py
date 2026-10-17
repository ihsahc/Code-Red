"""Database connection.

Locally this is a SQLite file (backend/dispensers.db) that needs no setup.
On Render, DATABASE_URL points at a Postgres database instead.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config

_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def add_missing_columns(bind: Engine) -> list[str]:
    """Add new optional columns to tables that already exist.

    create_all() makes missing tables but never changes existing ones, so a
    column added to models.py later wouldn't reach the live database. This
    adds any missing nullable column. (A bigger project would use Alembic.)
    """
    added = []
    existing_tables = set(inspect(bind).get_table_names())
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in inspect(conn).get_columns(table.name)}
            for col in table.columns:
                if col.name not in have and col.nullable:
                    col_type = col.type.compile(dialect=bind.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {col_type}'))
                    added.append(f"{table.name}.{col.name}")
    return added


def get_db() -> Iterator[Session]:
    """Give each request its own database session and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
