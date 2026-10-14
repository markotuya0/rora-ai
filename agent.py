"""Phase 2 agent loop: intent router, schema pruner, retry helpers, telemetry.

Stdlib-only so unit tests run without fastapi/langchain installed.
"""

import re

KNOWN_COLUMNS = ["id", "name", "subject", "score", "grade"]
KNOWN_TABLES = ["grades"]
KNOWN_SUBJECTS = ["Math", "History", "Science"]

MAX_RETRIES = 2  # retries after initial attempt => up to 3 total passes

_AGG = re.compile(r"\b(avg|average|sum|count|total|min|max|mean)\b", re.I)
_RANK = re.compile(r"\b(top|highest|lowest|best|worst|order by|rank|first|last)\b", re.I)
_META = re.compile(r"\b(schema|tables?|columns?|describe)\b", re.I)
_JOIN = re.compile(r"\b(join|combine|together|across|both)\b", re.I)
_TREND = re.compile(r"\b(trend|over time|by subject|group by|per )\b", re.I)
_OUT_OF_DOMAIN = re.compile(
    r"\b(customers?|churn(?:ed|s)?|revenue|orders?|products?|invoices?|employees?|sales|subscriptions?|users?|transactions?|payments?)\b",
    re.I,
)
_IN_DOMAIN = re.compile(
    r"\b(students?|names?|subjects?|math|history|science|scores?|grades?|marks?|class(?:es)?|" + "|".join(KNOWN_COLUMNS) + r")\b",
    re.I,
)


def is_in_scope(question: str) -> bool:
    """Fail-open domain check: reject only when the question is about data this demo does not have."""
    q = question or ""
    return not (_OUT_OF_DOMAIN.search(q) and not _IN_DOMAIN.search(q))


def route_intent(question: str) -> str:
    """Classify NL question into aggregate|filter|rank|join|trend|metadata."""
    q = question or ""
    if _META.search(q):
        return "metadata"
    if _JOIN.search(q):
        return "join"
    if _AGG.search(q):
        return "aggregate"
    if _RANK.search(q):
        return "rank"
    if _TREND.search(q):
        return "trend"
    return "filter"


def prune_schema(schema: str, question: str, intent: str) -> dict:
    """Prune full schema text to referenced columns.

    Returns dict with pruned_schema, tables_kept, columns_kept,
    tokens_full_est, tokens_pruned_est, reduction_pct.
    Token estimate: ~4 chars per token (rough, deterministic).
    """
    q = (question or "").lower()
    cols = [c for c in KNOWN_COLUMNS if c in q]
    # Intent-driven defaults: aggregates/ranks need score; filters often need subject/grade/name
    if intent in ("aggregate", "rank", "trend") and "score" not in cols:
        cols.append("score")
    if intent == "filter" and not cols:
        cols = ["name", "subject", "score", "grade"]
    if not cols:
        cols = list(KNOWN_COLUMNS)

    pruned = f"grades({', '.join(cols)})"
    full_est = max(1, len(schema or "") // 4)
    pruned_est = max(1, len(pruned) // 4)
    reduction = round(100 * (1 - pruned_est / full_est), 1) if full_est else 0.0
    return {
        "pruned_schema": pruned,
        "tables_kept": ["grades"],
        "columns_kept": cols,
        "tokens_full_est": full_est,
        "tokens_pruned_est": pruned_est,
        "reduction_pct": reduction,
    }


def trim_error(err: Exception | str, max_len: int = 300) -> str:
    """Trim DB/LLM errors for retry feedback (no secrets, no traceback)."""
    msg = str(err) if isinstance(err, Exception) else (err or "")
    msg = msg.split("[SQL:")[0]  # SQLAlchemy appends the full statement; keep it out of user-facing errors
    msg = re.sub(r"(password|secret|token|api[_-]?key)\s*=\s*\S+", r"\1=***", msg, flags=re.I)
    msg = " ".join(msg.split())
    return msg[:max_len]


def build_retry_input(question: str, pruned_schema: str, prior_sql: str, error: str) -> dict:
    """Build second-pass chain input with trimmed error feedback."""
    return {
        "schema": pruned_schema,
        "question": (
            f"{question}\n\nPrevious SQL failed validation/execution. "
            f"Prior SQL: {prior_sql}\nError: {error}\n"
            f"Return ONLY a corrected SELECT query."
        ),
    }


def missing_subject_filters(question: str, sql: str) -> list:
    """Subjects the question names that the SQL never mentions (deterministic, no LLM call)."""
    q = (question or "").lower()
    s = (sql or "").lower()
    return [subj for subj in KNOWN_SUBJECTS if re.search(rf"\b{subj.lower()}\b", q) and subj.lower() not in s]


DEMO_EXAMPLES = [
    "Average score per subject",
    "Top 3 students in Math",
    "Who scored below 70?",
    "How many students got an A?",
]


def prune_live_schema(schema: str, question: str, tables) -> dict:
    """Real-data pruning: keep only the tables the question names; fall back to the full schema.

    Works on sqlite CREATE TABLE blocks or postgres 'table.column (type)' lines.
    """
    q = (question or "").lower()
    names = sorted({t.lower() for t in tables})
    mentioned = {t for t in names if re.search(rf"\b{re.escape(t)}\b", q)}
    pruned = schema
    if mentioned:
        if "CREATE" in schema.upper():
            chunks = [c for c in re.split(r"(?=CREATE\s+TABLE)", schema, flags=re.IGNORECASE) if c.strip()]
            kept = [c for c in chunks if any(re.search(rf"\b{re.escape(t)}\b", c.lower()) for t in mentioned)]
            pruned = "\n".join(c.strip() for c in kept) or schema
        else:
            kept = [ln for ln in schema.splitlines() if ln.split(".", 1)[0].strip().lower() in mentioned]
            pruned = "\n".join(kept) or schema
    full_est = max(1, len(schema or "") // 4)
    pruned_est = max(1, len(pruned) // 4)
    return {
        "pruned_schema": pruned,
        "tables_kept": sorted(mentioned) or names,
        "columns_kept": [],
        "tokens_full_est": full_est,
        "tokens_pruned_est": pruned_est,
        "reduction_pct": round(100 * (1 - pruned_est / full_est), 1),
    }


def normalize_question(question: str) -> str:
    """Lowercase, drop punctuation, collapse spaces: 'Who scored below 70?' -> 'who scored below 70'."""
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (question or "").lower()).split())


DEMO_SAVED_SQL = {
    normalize_question("Average score per subject"): "SELECT subject, AVG(score) FROM grades GROUP BY subject",
    normalize_question("Top 3 students in Math"): "SELECT name, score FROM grades WHERE subject = 'Math' ORDER BY score DESC LIMIT 3",
    normalize_question("Who scored below 70?"): "SELECT name, subject, score FROM grades WHERE score < 70",
    normalize_question("How many students got an A?"): "SELECT COUNT(*) FROM grades WHERE grade = 'A'",
}


def saved_sql(question: str):
    """SQL for a known demo question, or None. The caller still runs it through the safety guard."""
    return DEMO_SAVED_SQL.get(normalize_question(question))
