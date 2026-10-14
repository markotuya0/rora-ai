"""api/v1 routes: query, history, schema, health.

Deps (db, sql_chain, history) are resolved lazily from the app module to
avoid a circular import at module load time.
"""
from fastapi import APIRouter, Query, Request, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import time
from datetime import datetime, timezone

from rora_api.core.auth import verify_token, require_scope
from rora_api.core.rate_limit import check_rate_limit
from rora_api.core.pagination import paginated
from config import MAX_QUERY_LENGTH, DEMO_MODE, LLM_MODEL
from utils import clean_sql, validate_sql, ensure_limit, new_request_id, tables_from_schema
from agent import (
    route_intent, prune_schema, prune_live_schema, trim_error, build_retry_input,
    is_in_scope, missing_subject_filters, DEMO_EXAMPLES, MAX_RETRIES, normalize_question, saved_sql,
)
import hashlib
from collections import OrderedDict

# Successful model answers, keyed by (normalized question, schema hash). Results are never cached, only SQL.
_sql_cache: OrderedDict = OrderedDict()
_SQL_CACHE_MAX = 128
from ops.payloads import synthesize_actions
from ops.audit import log_event

router = APIRouter(prefix="/api/v1", tags=["v1"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class QueryResponse(BaseModel):
    question: str
    sql_query: str
    result: str
    timestamp: str
    success: bool
    execution_time: Optional[float] = None
    request_id: Optional[str] = None
    telemetry: Optional[dict] = None
    actions: Optional[dict] = None


def _claims(request: Request):
    return verify_token(request.headers.get("authorization", "").removeprefix("Bearer ").strip())


def _require(request: Request, scope: str):
    claims = _claims(request)
    if not require_scope(claims, scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient scope: {scope}")
    check_rate_limit(request)


def _run_query(request: QueryRequest, db, sql_chain) -> QueryResponse:
    """Shared query pipeline (kept identical to api.py execute_query)."""
    start_time = time.time()
    request_id = new_request_id()
    t_router = t_prune = t_llm = t_db = 0.0
    attempts = 0
    last_error = ""
    last_kind = ""
    intent = "filter"

    t0 = time.time()
    if DEMO_MODE and not is_in_scope(request.question):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("This demo only has student grades (name, subject, score, grade). "
                    "Try: " + "; ".join(f"'{q}'" for q in DEMO_EXAMPLES[:3])),
        )
    intent = route_intent(request.question)
    t_router = time.time() - t0

    t0 = time.time()
    full_schema = db.get_table_info()
    if DEMO_MODE:
        pruned = prune_schema(full_schema, request.question, intent)
    else:
        pruned = prune_live_schema(full_schema, request.question, tables_from_schema(full_schema))
    pruned_schema = pruned["pruned_schema"]
    t_prune = time.time() - t0

    sql_query = ""
    result = None
    ast_verdict = "pass"

    chain_input = {"schema": pruned_schema, "question": request.question}

    # A known demo question or a repeated question skips the model on the first attempt.
    # The SQL still goes through the guard and the DB below; if it fails, the model takes over.
    cache_key = (normalize_question(request.question), hashlib.sha256(full_schema.encode()).hexdigest()[:16])
    prefilled = saved_sql(request.question) if DEMO_MODE else None
    source = "example" if prefilled else None
    if prefilled is None and cache_key in _sql_cache:
        prefilled, source = _sql_cache[cache_key], "cache"
    if source is None:
        source = "model"

    for attempt in range(1, MAX_RETRIES + 2):
        attempts = attempt
        if prefilled is not None:
            raw_sql, prefilled = prefilled, None
        else:
            t0 = time.time()
            raw_sql = sql_chain.invoke(chain_input)
            t_llm += time.time() - t0
        sql_query = clean_sql(raw_sql)
        from_prefill = source != "model" and attempt == 1

        # Fail closed: only tables present in the live schema may be referenced (blocks UNION/subquery exfil).
        ok, reason, _ = validate_sql(sql_query, allowed_tables=tables_from_schema(full_schema))
        if not ok:
            ast_verdict = f"reject: {reason}"
            last_error = reason
            last_kind = "ast"
            if from_prefill:
                _sql_cache.pop(cache_key, None)
                source = "model"
            chain_input = build_retry_input(request.question, pruned_schema, sql_query, trim_error(reason))
            continue

        # Semantic check: a subject named in the question must be filtered on, or the answer is wrong.
        missing = missing_subject_filters(request.question, sql_query)
        if DEMO_MODE and missing:
            last_error = f"query must filter on subject {', '.join(missing)} named in the question"
            last_kind = "semantic"
            if from_prefill:
                _sql_cache.pop(cache_key, None)
                source = "model"
            chain_input = build_retry_input(request.question, pruned_schema, sql_query, trim_error(last_error))
            continue

        sql_query = ensure_limit(sql_query)
        t0 = time.time()
        try:
            result = db.run(sql_query)
            t_db += time.time() - t0
            if source == "model":
                _sql_cache[cache_key] = clean_sql(raw_sql)
                _sql_cache.move_to_end(cache_key)
                while len(_sql_cache) > _SQL_CACHE_MAX:
                    _sql_cache.popitem(last=False)
            break
        except Exception as e:
            t_db += time.time() - t0
            last_error = trim_error(e)
            last_kind = "db"
            if from_prefill:
                _sql_cache.pop(cache_key, None)
                source = "model"
            chain_input = build_retry_input(request.question, pruned_schema, sql_query, last_error)
            continue

    if result is None:
        if last_kind == "ast":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Unsafe SQL rejected after {attempts} attempts: {last_error}.")
        detail = f"Query failed after {attempts} attempts"
        if last_error:
            detail += f": {last_error}"
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"{detail} (request_id={request_id}).")

    execution_time = time.time() - start_time
    telemetry = {
        "request_id": request_id,
        "intent": intent,
        "tables": pruned["tables_kept"],
        "columns_kept": pruned["columns_kept"],
        "tokens_full_est": pruned["tokens_full_est"],
        "tokens_pruned_est": pruned["tokens_pruned_est"],
        "reduction_pct": pruned["reduction_pct"],
        "latency_ms": {
            "total": round(execution_time * 1000, 1),
            "router": round(t_router * 1000, 1),
            "prune": round(t_prune * 1000, 1),
            "llm": round(t_llm * 1000, 1),
            "db": round(t_db * 1000, 1),
        },
        "ast_verdict": ast_verdict,
        "attempts": attempts,
        "source": source,
    }

    actions = synthesize_actions(request.question, sql_query, result, intent)
    if actions.get("email_draft") or actions.get("gtm_triggers"):
        log_event(
            "actions.synthesized",
            {"request_id": request_id, "cs_tags": actions.get("cs_tags"), "triggers": len(actions.get("gtm_triggers", []))},
            request_id=request_id,
        )

    return QueryResponse(
        question=request.question,
        sql_query=sql_query,
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat(),
        success=True,
        execution_time=round(execution_time, 3),
        request_id=request_id,
        telemetry=telemetry,
        actions=actions,
    )


@router.post("/query", response_model=QueryResponse)
def v1_query(request: QueryRequest, req: Request):
    _require(req, "read:query")
    import api as app_module
    response = _run_query(request, app_module.db, app_module.sql_chain)
    # Record the run so /history and /actions/approve can find it by request_id.
    app_module.query_history.append(response.model_dump())
    return response


@router.get("/history")
def v1_history(limit: int = Query(10, ge=1, le=100), cursor: Optional[str] = None,
               req: Request = None):
    _require(req, "read:query")
    import api as app_module
    return paginated(app_module.query_history, limit, cursor)


@router.get("/schema")
def v1_schema(req: Request):
    _require(req, "read:query")
    import api as app_module
    return {"schema": app_module.db.get_table_info()}


@router.get("/health")
def v1_health():
    import api as app_module
    from config import LLM_MODEL
    try:
        ok = app_module.db.healthcheck()
        if not ok:
            raise RuntimeError("db healthcheck failed")
        return {"status": "healthy", "model": LLM_MODEL, "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Service unhealthy: {e}")


@router.get("/config")
def v1_config(req: Request):
    """What the UI needs to show: demo or live mode, the tables it can query, example questions."""
    _require(req, "read:query")
    import api as app_module
    tables = sorted(tables_from_schema(app_module.db.get_table_info()))
    return {
        "demo_mode": DEMO_MODE,
        "tables": tables,
        "examples": DEMO_EXAMPLES if DEMO_MODE else [],
        "llm_model": LLM_MODEL,
    }


@router.get("/sample")
def v1_sample(req: Request, rows: int = Query(5, ge=1, le=20)):
    """Read-only profile of the connected database: what tables exist, row counts, sample rows and column stats."""
    _require(req, "read:query")
    import api as app_module
    return {"demo_mode": DEMO_MODE, **app_module.db.profile(rows)}
