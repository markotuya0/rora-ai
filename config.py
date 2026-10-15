import os
from pathlib import Path

# Project Configuration
PROJECT_NAME = "Rora AI"
VERSION = "1.0.0"
DESCRIPTION = "AI-powered Text-to-SQL application"

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "student_grades.db")
# DB_URI wins when set (e.g. postgresql://user:pass@host/db); otherwise the local SQLite file.
DB_URI = os.getenv("DB_URI") or f"sqlite:///{DB_PATH}"
# DEMO_MODE=true: bundled student-grades demo, demo-only guards and examples.
# DEMO_MODE=false: your own database, schema read live, demo-only guards off.
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"

# App Configuration
APP_TITLE = "🤖 Rora AI - Text-to-SQL"
APP_DESCRIPTION = "Transform natural language into SQL queries with AI"

# Security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "500"))
