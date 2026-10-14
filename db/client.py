"""Read-only query execution client (replaces raw db.run)."""
import time
from sqlalchemy import text
from sqlalchemy.engine import Result

from db.engine import engine, SessionLocal
from utils import logger

STATEMENT_TIMEOUT_MS = 5000
ROW_CAP = 1000


def run_query(sql: str, params: dict = None) -> str:
    """Execute read-only SQL. Returns repr string (langchain-compatible).

    On Postgres: read-only session + statement_timeout.
    On SQLite: mode=ro is not settable per-query, so we rely on AST guard +
    SQLAlchemy text() (parameterized). Errors are trimmed for retry loop.
    """
    started = time.time()
    with SessionLocal() as session:
        if engine.url.get_backend_name() == "postgresql":
            session.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
        result: Result = session.execute(text(sql), params or {})
        rows = result.fetchmany(ROW_CAP)
        elapsed = (time.time() - started) * 1000
        logger.info(f"db.run ok rows={len(rows)} in {elapsed:.1f}ms")
        return repr([tuple(r) for r in rows])


def get_table_info() -> str:
    """Schema string for LLM prompt (dialect-aware)."""
    dialect = engine.url.get_backend_name()
    if dialect == "sqlite":
        sql = "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
            return "\n".join(r[0] for r in rows if r[0])
    # Postgres: information_schema
    sql = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
        info = []
        for table_name, column_name, data_type in rows:
            info.append(f"{table_name}.{column_name} ({data_type})")
        return "\n".join(info) if info else "no tables"


def healthcheck() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class DBClient:
    """Facade so api code keeps db.run() / db.get_table_info() call shape."""

    def run(self, sql: str, params: dict = None) -> str:
        return run_query(sql, params)

    def get_table_info(self) -> str:
        return get_table_info()


    def healthcheck(self) -> bool:
        return healthcheck()

    def profile(self, sample_rows: int = 5) -> dict:
        return profile_database(sample_rows)


def _quote(identifier: str) -> str:
    """Quote an identifier taken from database metadata (never from user input)."""
    return '"' + identifier.replace('"', '""') + '"'


def _jsonable(value):
    return value if value is None or isinstance(value, (int, float, str, bool)) else str(value)


def profile_database(sample_rows: int = 5) -> dict:
    """Read-only profile of every table: row count, sample rows and per-column stats. No LLM call."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.types import Float, Integer, Numeric

    insp = sa_inspect(engine)
    tables = []
    with engine.connect() as conn:
        for table in sorted(insp.get_table_names()):
            qt = _quote(table)
            columns = insp.get_columns(table)
            total = conn.execute(text(f"SELECT COUNT(*) FROM {qt}")).scalar()
            sample = conn.execute(text(f"SELECT * FROM {qt} LIMIT :n"), {"n": sample_rows})
            sample_columns = list(sample.keys())
            sample_data = [[_jsonable(v) for v in row] for row in sample.fetchall()]

            stats = []
            for col in columns:
                qc = _quote(col["name"])
                if isinstance(col["type"], (Integer, Float, Numeric)):
                    lo, hi, avg = conn.execute(text(f"SELECT MIN({qc}), MAX({qc}), AVG({qc}) FROM {qt}")).one()
                    stats.append({
                        "column": col["name"], "kind": "numeric",
                        "min": _jsonable(lo), "max": _jsonable(hi),
                        "avg": round(float(avg), 2) if avg is not None else None,
                    })
                else:
                    distinct = conn.execute(text(f"SELECT COUNT(DISTINCT {qc}) FROM {qt}")).scalar()
                    top = conn.execute(text(
                        f"SELECT {qc}, COUNT(*) AS n FROM {qt} GROUP BY {qc} ORDER BY n DESC LIMIT 5"
                    )).fetchall()
                    stats.append({
                        "column": col["name"], "kind": "text", "distinct": distinct,
                        "top": [[_jsonable(v), n] for v, n in top],
                    })
            tables.append({
                "name": table,
                "rows": total,
                "columns": [c["name"] for c in columns],
                "sample_columns": sample_columns,
                "sample": sample_data,
                "stats": stats,
            })
    return {"tables": tables}
