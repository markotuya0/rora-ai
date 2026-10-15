"""20-case regression suite (ARCHITECTURE_v2 §6).

Run: pytest eval/test_regression_20.py -q
Pure-python cases (c08, c09) run without fastapi; API cases skip if fastapi missing.
"""
import pytest
from eval.cases import CASES


# ---------- pure-python cases (no fastapi needed) ----------

def test_c08_safe_select():
    from utils import is_safe_query
    assert is_safe_query("SELECT * FROM grades") is True


def test_c09_safe_unsafe():
    from utils import is_safe_query
    assert is_safe_query("DROP TABLE grades") is False


# ---------- API cases (skip if fastapi/httpx missing) ----------

def _post(client, question):
    return client.post("/api/v1/query", json={"question": question})


def test_c01_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_c02_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_c03_schema(client, mock_db):
    r = client.get("/api/v1/schema")
    assert r.status_code == 200
    assert "schema" in r.json()


def test_c04_query_valid(client, mock_chain, mock_db):
    r = _post(client, "Show all students")
    assert r.status_code == 200
    assert "SELECT" in r.json()["sql_query"]


def test_c05_history(client):
    r = client.get("/api/v1/history")
    assert r.status_code == 200
    assert "history" in r.json() or "items" in r.json()


def test_c06_clean_fence(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "```sql\nSELECT * FROM grades\n```"
    r = _post(client, "Show all students")
    assert r.status_code == 200
    assert "SELECT" in r.json()["sql_query"]


def test_c07_clean_plain(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT * FROM grades"
    r = _post(client, "Show all students")
    assert r.status_code == 200
    assert r.json()["sql_query"].startswith("SELECT")


def test_c10_stacked(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT * FROM grades; DROP TABLE grades"
    r = _post(client, "stacked")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "UNSAFE_SQL"


def test_c11_union_exfil(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT * FROM grades UNION SELECT * FROM secrets"
    r = _post(client, "exfil")
    assert r.status_code == 400


def test_c12_multi_statement(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT 1; SELECT 2"
    r = _post(client, "multi")
    assert r.status_code == 400


def test_c13_limit_injected(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT * FROM grades"
    r = _post(client, "Show all students")
    assert r.status_code == 200
    assert "LIMIT" in r.json()["sql_query"].upper()


def test_c14_retry_unknown_column(client, mock_chain, mock_db):
    mock_chain.invoke.side_effect = ["SELECT foo FROM grades", "SELECT name FROM grades"]
    mock_db.run.side_effect = [Exception("no such column: foo"), "[('Aman',)]"]
    r = _post(client, "show names")
    assert r.status_code == 200
    assert r.json()["telemetry"]["attempts"] == 2


def test_c15_retry_db_error(client, mock_chain, mock_db):
    mock_chain.invoke.side_effect = ["SELECT foo FROM grades", "SELECT name FROM grades"]
    mock_db.run.side_effect = [Exception("no such column: foo"), "[('Aman',)]"]
    r = _post(client, "show names")
    assert r.status_code == 200
    assert r.json()["telemetry"]["attempts"] == 2


def test_c16_retry_exhausted(client, mock_chain, mock_db):
    mock_chain.invoke.return_value = "SELECT * FROM grades"  # real table: exercises the DB-error path, not the schema guard
    mock_db.run.side_effect = Exception("no such table")
    r = _post(client, "missing")
    assert r.status_code == 500
    assert mock_chain.invoke.call_count == 3


def test_c17_history_limit_neg(client):
    assert client.get("/api/v1/history?limit=-1").status_code == 422
    assert client.get("/api/v1/history?limit=200").status_code == 422


def test_c18_question_oversized(client):
    r = _post(client, "x" * 600)
    assert r.status_code == 422


def test_c19_empty_db_result(client, mock_chain, mock_db):
    mock_db.run.return_value = "[]"
    r = _post(client, "Show all students")
    assert r.status_code == 200
    assert "actions" in r.json()


def test_c20_telemetry_fields(client, mock_chain, mock_db):
    r = _post(client, "Show all students")
    assert r.status_code == 200
    t = r.json()["telemetry"]
    for k in ("request_id", "intent", "latency_ms", "ast_verdict", "attempts"):
        assert k in t
