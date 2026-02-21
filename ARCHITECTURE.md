# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Streamlit UI (app_v2.py)                                   │
│  - User input interface                                      │
│  - Query history display                                     │
│  - Real-time results visualization                           │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
├─────────────────────────────────────────────────────────────┤
│  api.py                                                      │
│  - POST /query      - Execute NL queries                    │
│  - GET  /history    - Retrieve query history                │
│  - GET  /schema     - Database schema info                  │
│  - GET  /health     - Health check                          │
└────────────┬───────────────────────┬────────────────────────┘
             │                       │
             ▼                       ▼
┌────────────────────────┐  ┌──────────────────────────────┐
│   AI/LLM Layer         │  │   Data Layer                 │
├────────────────────────┤  ├──────────────────────────────┤
│  LangChain + Ollama    │  │  SQLite Database             │
│  - Text-to-SQL         │  │  - student_grades table      │
│  - Query generation    │  │  - Query execution           │
│  - Prompt engineering  │  │  - Schema management         │
└────────────────────────┘  └──────────────────────────────┘
```

## Data Flow

1. **User Input** → Streamlit UI receives natural language question
2. **API Request** → Frontend sends POST to `/query` endpoint
3. **LLM Processing** → LangChain + Ollama generates SQL query
4. **Validation** → Security check (SELECT-only queries)
5. **Execution** → SQL runs against SQLite database
6. **Response** → Results returned to frontend
7. **History** → Query logged for future reference

## Key Components

### 1. Frontend (Streamlit)
- **Purpose**: User interface for query input and result display
- **Features**: Real-time updates, query history, metrics
- **Tech**: Streamlit, Requests

### 2. Backend (FastAPI)
- **Purpose**: REST API for query processing
- **Features**: Auto-generated docs, CORS, validation
- **Tech**: FastAPI, Pydantic, Uvicorn

### 3. AI Layer (LangChain + Ollama)
- **Purpose**: Natural language to SQL translation
- **Features**: Local LLM, prompt templates, output parsing
- **Tech**: LangChain, Ollama (Qwen 2.5)

### 4. Database (SQLite)
- **Purpose**: Data storage and query execution
- **Features**: Lightweight, serverless, SQL support
- **Tech**: SQLite, SQLAlchemy

## Security Measures

1. **Query Validation**: Only SELECT statements allowed
2. **SQL Injection Prevention**: Parameterized queries
3. **Local Processing**: No external API calls
4. **CORS Configuration**: Controlled access
5. **Input Validation**: Pydantic models

## Performance Optimizations

1. **Caching**: Streamlit resource caching for DB/LLM
2. **Connection Pooling**: Reuse database connections
3. **Async Operations**: FastAPI async endpoints
4. **Lightweight Model**: Qwen 2.5 (0.5B parameters)

## Deployment Options

### Development
```bash
python api.py
streamlit run app_v2.py
```

### Production (Docker)
```bash
docker-compose up -d
```

### Cloud Deployment
- AWS: ECS/Fargate + RDS
- GCP: Cloud Run + Cloud SQL
- Azure: Container Apps + Azure SQL

## Monitoring & Observability

- **Health Checks**: `/health` endpoint
- **Logging**: Python logging module
- **Benchmarking**: `benchmark.py` script
- **Testing**: Unit tests + API tests

## Scalability Considerations

1. **Horizontal Scaling**: Multiple API instances behind load balancer
2. **Database**: Migrate to PostgreSQL for production
3. **Caching**: Add Redis for query results
4. **Queue**: Add Celery for async processing
5. **CDN**: Static assets via CloudFront/CloudFlare
