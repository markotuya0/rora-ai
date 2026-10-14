"""SQLAlchemy 2.0 engine factory. SQLite (dev) or PostgreSQL (prod) via DB_URI."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config import DB_URI

_is_postgres = DB_URI.startswith("postgresql://")


def get_engine(url: str = None):
    url = url or DB_URI
    if url.startswith("sqlite://"):
        # StaticPool + same-thread for in-memory/file SQLite across FastAPI workers
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in url else None,
        )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def set_readonly(dbapi_conn, _):
    """Read-only enforcement on Postgres; SQLite gets mode=ro URI instead."""
    if _is_postgres:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
        cursor.close()


if _is_postgres:
    event.listen(engine, "connect", set_readonly)
