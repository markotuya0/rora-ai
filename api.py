from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import sqlite3
from datetime import datetime

from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import (
    DB_URI, LLM_MODEL, LLM_TEMPERATURE, PROJECT_NAME, 
    VERSION, DESCRIPTION, ALLOWED_ORIGINS, MAX_QUERY_LENGTH
)
from utils import clean_sql, is_safe_query, logger

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
    
    @validator('question')
    def validate_question(cls, v):
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
    """Execute a natural language query and return SQL results"""
    import time
    start_time = time.time()
    
    try:
        schema = db.get_table_info()
        raw_sql = sql_chain.invoke({"schema": schema, "question": request.question})
        sql_query = clean_sql(raw_sql)
        
        if not is_safe_query(sql_query):
            logger.warning(f"Unsafe query blocked: {sql_query}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only SELECT queries are allowed for security reasons"
            )
        
        result = db.run(sql_query)
        execution_time = time.time() - start_time
        
        response = QueryResponse(
            question=request.question,
            sql_query=sql_query,
            result=result,
            timestamp=datetime.now().isoformat(),
            success=True,
            execution_time=round(execution_time, 3)
        )
        
        query_history.append(response.dict())
        logger.info(f"Query executed successfully in {execution_time:.3f}s: {request.question}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )

@app.get("/history")
def get_history(limit: int = 10, skip: int = 0):
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
