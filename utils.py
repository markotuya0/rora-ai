import json
import re
import logging
import uuid

# Structured JSON logging (Phase 0: requestId-ready)
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        return json.dumps(payload)

_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logger = logging.getLogger("rora-ai")
logger.handlers = [_handler]
logger.setLevel(logging.INFO)
logger.propagate = False


def new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def clean_sql(text: str) -> str:
    """Remove markdown code fences from LLM output (robust, multi-fence)."""
    t = text.strip()
    # ```sql ... ``` or ``` ... ``` (possibly multiple)
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    # inline single fence pair
    if t.startswith("```") and t.endswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"```$", "", t)
    return t.strip().rstrip(";").strip()


def _ast_verdict(sql: str, allowed_tables=None):
    """Parse with sqlglot and enforce SELECT/JOIN-only policy.

    Returns (ok: bool, reason: str, tables: list[str]).
    """
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError:
        return False, "sqlglot not installed", []

    statements = [s.strip() for s in sql.strip().split(";") if s.strip()]
    if len(statements) > 1:
        return False, "multiple statements not allowed", []
    if "--" in sql or "/*" in sql:
        return False, "SQL comments not allowed", []

    try:
        tree = sqlglot.parse_one(sql, read="sqlite")
    except Exception as e:
        return False, f"SQL parse failed: {e}", []

    if tree is None:
        return False, "empty or unparsable SQL", []

    # Only SELECT / UNION of SELECTs / WITH...SELECT allowed
    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        # WITH queries parse as Select with .args['with']; CTE wrapping DML still caught below
        if not isinstance(tree, exp.Select):
            return False, f"only SELECT queries allowed, got {tree.key.upper()}", []

    forbidden = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop,
        exp.Create, exp.Alter, exp.TruncateTable, exp.Grant,
        exp.Copy,
    )
    for node in tree.walk(bfs=False):
        n = node[0] if isinstance(node, tuple) else node
        if isinstance(n, forbidden):
            return False, f"forbidden statement: {n.key.upper()}", []

    tables = [t.name.lower() for t in tree.find_all(exp.Table)]
    if allowed_tables is not None:
        allowed = {a.lower() for a in allowed_tables}
        unknown = [t for t in tables if t not in allowed]
        if unknown:
            return False, f"unknown tables: {unknown}", tables

    return True, "pass", tables


def is_safe_query(sql: str, allowed_tables=None) -> bool:
    """AST-based SELECT/JOIN-only safety check (replaces startswith guard)."""
    ok, _, _ = _ast_verdict(sql, allowed_tables)
    return ok


def validate_sql(sql: str, allowed_tables=None):
    """Return (ok, reason, tables) for callers needing diagnostics."""
    return _ast_verdict(sql, allowed_tables)


def ensure_limit(sql: str, default_limit: int = 200, max_limit: int = 1000) -> str:
    """Inject LIMIT if missing; clamp existing LIMIT to max_limit. AST-based."""
    try:
        import sqlglot
        from sqlglot import exp
        tree = sqlglot.parse_one(sql, read="sqlite")
    except Exception:
        return sql
    if not isinstance(tree, exp.Select):
        return sql
    existing = tree.args.get("limit")
    if existing is None:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(default_limit)))
    else:
        try:
            n = int(existing.expression.name)
            if n > max_limit:
                tree.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
        except (ValueError, AttributeError):
            pass
    return tree.sql(dialect="sqlite")

def log_query(question: str, sql: str, success: bool):
    """Log query execution for monitoring."""
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"{status} | Question: {question} | SQL: {sql}")


_CREATE_TABLE_RE = re.compile(r'CREATE\s+TABLE\s+(?:IF NOT EXISTS\s+)?"?(\w+)"?', re.IGNORECASE)


def tables_from_schema(schema: str) -> set:
    """Table names from get_table_info() output (sqlite CREATE TABLE or postgres 'table.column (type)')."""
    names = set(_CREATE_TABLE_RE.findall(schema))
    names |= set(re.findall(r"^(\w+)\s*\(", schema, re.MULTILINE))  # "grades(id, name)" prompt format
    names |= {line.split(".", 1)[0].strip() for line in schema.splitlines() if "." in line and " (" in line}
    return {n.lower() for n in names if n}
