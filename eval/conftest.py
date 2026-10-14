"""Shared pytest fixtures: mocked chain/db, TestClient.

Pure-python fixtures work without fastapi; API fixtures skip via importorskip.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_chain():
    with patch("api.sql_chain") as m:
        m.invoke.return_value = "SELECT * FROM grades"
        yield m


@pytest.fixture
def mock_db():
    with patch("api.db") as m:
        m.run.return_value = "[(1, 'Aman', 'Math', 95, 'A')]"
        m.get_table_info.return_value = "grades(id, name, subject, score, grade)"
        m.healthcheck.return_value = True
        yield m


@pytest.fixture
def client():
    fastapi = pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    import api
    from api import app
    api.query_history.clear()
    with TestClient(app) as c:
        yield c
