"""Phase 2 agent loop: intent router, schema pruner, retry helpers, telemetry.

Stdlib-only so unit tests run without fastapi/langchain installed.
"""

import re

KNOWN_COLUMNS = ["id", "name", "subject", "score", "grade"]
KNOWN_TABLES = ["grades"]

MAX_RETRIES = 2  # retries after initial attempt => up to 3 total passes

_AGG = re.compile(r"\b(avg|average|sum|count|total|min|max|mean)\b", re.I)
_RANK = re.compile(r"\b(top|highest|lowest|best|worst|order by|rank|first|last)\b", re.I)
_META = re.compile(r"\b(schema|tables?|columns?|describe)\b", re.I)
_JOIN = re.compile(r"\b(join|combine|together|across|both)\b", re.I)
_TREND = re.compile(r"\b(trend|over time|by subject|group by|per )\b", re.I)


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
