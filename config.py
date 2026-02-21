import os
from pathlib import Path

# Project Configuration
PROJECT_NAME = "Rora AI"
VERSION = "1.0.0"
DESCRIPTION = "AI-powered Text-to-SQL application"

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "student_grades.db")
DB_URI = f"sqlite:///{DB_PATH}"

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:0.5b")
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
