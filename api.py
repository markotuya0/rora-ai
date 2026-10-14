from fastapi import FastAPI, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from db.client import DBClient

from config import (
    DB_URI, LLM_MODEL, LLM_TEMPERATURE, PROJECT_NAME, 
    VERSION, DESCRIPTION, ALLOWED_ORIGINS, MAX_QUERY_LENGTH
)
from utils import clean_sql, is_safe_query, validate_sql, ensure_limit, logger, new_request_id
from agent import route_intent, prune_schema, trim_error, build_retry_input, MAX_RETRIES
from rora_api.core.errors import (
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from rora_api.core.pagination import paginated
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from rora_api.v1.routes import router as v1_router
from rora_api.v1.actions import router as v1_actions_router
from rora_api.core.auth import AUTH_ENABLED

# Initialize FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Phase 3: standard error envelope handlers (api-design-reviewer)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Phase 3: versioned API
app.include_router(v1_router)
app.include_router(v1_actions_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
db = DBClient()
llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE, num_predict=256, num_ctx=2048, keep_alive="30m")

prompt = ChatPromptTemplate.from_template("""
You are a SQL expert. Return only one SQLite SELECT statement. No explanation, no markdown.
Include a WHERE condition for every subject, name or value the question mentions.
When the question asks for a value per group, select the group column too so each value is labelled.
Schema: {schema}
Question: {question}
""")

sql_chain = prompt | llm | StrOutputParser()

# In-memory cache
query_history = []

# --- Legacy routes: 308 redirects to /api/v1 (one release, per api-design-reviewer) ---

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


@app.get("/query", include_in_schema=False)
def legacy_query():
    return RedirectResponse(url="/api/v1/query", status_code=status.HTTP_308_PERMANENT_REDIRECT)


@app.post("/query", include_in_schema=False)
def legacy_query_post():
    return RedirectResponse(url="/api/v1/query", status_code=status.HTTP_308_PERMANENT_REDIRECT)


@app.get("/history", include_in_schema=False)
def legacy_history(limit: int = Query(10, ge=1, le=100), skip: int = Query(0, ge=0)):
    return RedirectResponse(url="/api/v1/history", status_code=status.HTTP_308_PERMANENT_REDIRECT)


@app.get("/schema", include_in_schema=False)
def legacy_schema():
    return RedirectResponse(url="/api/v1/schema", status_code=status.HTTP_308_PERMANENT_REDIRECT)


@app.get("/health", include_in_schema=False)
def legacy_health():
    return RedirectResponse(url="/api/v1/health", status_code=status.HTTP_308_PERMANENT_REDIRECT)

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
