from fastapi import FastAPI, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import sqlite3
import time
import uuid
from datetime import datetime

from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import (
    DB_URI, LLM_MODEL, LLM_TEMPERATURE, PROJECT_NAME, 
    VERSION, DESCRIPTION, ALLOWED_ORIGINS, MAX_QUERY_LENGTH
)
from utils import clean_sql, is_safe_query, validate_sql, ensure_limit, logger, new_request_id
from agent import route_intent, prune_schema, trim_error, build_retry_input, MAX_RETRIES

# Initialize FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
db = SQLDatabase.from_uri(DB_URI)
llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

prompt = ChatPromptTemplate.from_template("""
You are a SQL expert. Generate ONLY a SQL query for this question.
Schema: {schema}
Question: {question}
""")

sql_chain = prompt | llm | StrOutputParser()

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)

    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Question cannot be empty')
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

# In-memory cache
query_history = []

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": PROJECT_NAME,
        "version": VERSION,
        "description": DESCRIPTION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def execute_query(request: QueryRequest):
    """Execute a natural language query with intent routing, pruned schema, and ≤2-pass retry."""
    start_time = time.time()
    request_id = new_request_id()
    t_router = t_prune = t_llm = t_db = 0.0
    attempts = 0
    last_error = ""

    def _log(level: str, msg: str):
        getattr(logger, level)(msg, extra={"request_id": request_id})

    try:
        t0 = time.time()
        intent = route_intent(request.question)
        t_router = time.time() - t0

        t0 = time.time()
        full_schema = db.get_table_info()
        pruned = prune_schema(full_schema, request.question, intent)
        pruned_schema = pruned["pruned_schema"]
        t_prune = time.time() - t0
        _log("info",
             f"schema pruned intent={intent} tables={pruned['tables_kept']} "
             f"columns={pruned['columns_kept']} tokens_full={pruned['tokens_full_est']} "
             f"tokens_pruned={pruned['tokens_pruned_est']} reduction={pruned['reduction_pct']}%")

        sql_query = ""
        result = None
        ast_verdict = "pass"
        last_kind = ""

        chain_input = {"schema": pruned_schema, "question": request.question}
        for attempt in range(1, MAX_RETRIES + 2):  # initial + up to 2 retries
            attempts = attempt
            t0 = time.time()
            raw_sql = sql_chain.invoke(chain_input)
            t_llm += time.time() - t0
            sql_query = clean_sql(raw_sql)

            ok, reason, tables = validate_sql(sql_query)
            if not ok:
                ast_verdict = f"reject: {reason}"
                last_error = reason
                last_kind = "ast"
                _log("warning", f"attempt={attempt} AST reject: {reason} | sql={sql_query}")
                chain_input = build_retry_input(request.question, pruned_schema, sql_query, trim_error(reason))
                continue

            sql_query = ensure_limit(sql_query)
            t0 = time.time()
            try:
                result = db.run(sql_query)
                t_db += time.time() - t0
                break
            except Exception as e:
                t_db += time.time() - t0
                last_error = trim_error(e)
                last_kind = "db"
                _log("warning", f"attempt={attempt} DB error: {last_error}")
                chain_input = build_retry_input(request.question, pruned_schema, sql_query, last_error)
                continue

        if result is None:
            _log("warning", f"retry exhausted attempts={attempts} last_error={last_error}")
            if last_kind == "ast":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsafe SQL rejected after {attempts} attempts: {last_error}. Only SELECT/JOIN queries allowed."
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query failed after {attempts} attempts (request_id={request_id})."
            )

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
        }

        response = QueryResponse(
            question=request.question,
            sql_query=sql_query,
            result=result,
            timestamp=datetime.now().isoformat(),
            success=True,
            execution_time=round(execution_time, 3),
            request_id=request_id,
            telemetry=telemetry,
        )

        query_history.append(response.model_dump())
        _log("info", f"Query executed successfully in {execution_time:.3f}s attempts={attempts}: {request.question}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )

@app.get("/history")
def get_history(limit: int = Query(10, ge=1, le=100), skip: int = Query(0, ge=0)):
    """Retrieve query history with pagination"""
    total = len(query_history)
    history_slice = query_history[-(limit + skip):-skip] if skip > 0 else query_history[-limit:]
    return {
        "history": list(reversed(history_slice)),
        "total": total,
        "limit": limit,
        "skip": skip
    }

@app.get("/schema")
def get_schema():
    """Get database schema information"""
    return {"schema": db.get_table_info()}

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.get_table_info()
        return {
            "status": "healthy",
            "model": LLM_MODEL,
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT, API_RELOAD
    
    logger.info(f"Starting {PROJECT_NAME} v{VERSION}")
    logger.info(f"API server running on http://{API_HOST}:{API_PORT}")
    logger.info(f"API documentation available at http://{API_HOST}:{API_PORT}/docs")
    
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
