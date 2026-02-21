import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_sql(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```$", "", t)
    return t.strip()

def is_safe_query(sql: str) -> bool:
    """Check if query is a safe SELECT statement."""
    return sql.lower().lstrip().startswith("select")

def log_query(question: str, sql: str, success: bool):
    """Log query execution for monitoring."""
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"{status} | Question: {question} | SQL: {sql}")
