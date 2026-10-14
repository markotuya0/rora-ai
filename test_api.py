import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import api
from api import app

class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        api.query_history.clear()

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("name", body)
        self.assertIn("version", body)
        self.assertEqual(body["status"], "running")
    
    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
    
    def test_schema(self):
        response = self.client.get("/schema")
        self.assertEqual(response.status_code, 200)
        self.assertIn("schema", response.json())
    
    def test_query_valid(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "run", return_value="[(1, 'Aman', 'Math', 95, 'A')]") as mock_run, \
             patch.object(api.db, "get_table_info", return_value="grades(id, name, subject, score, grade)"):
            mock_chain.invoke.return_value = "SELECT * FROM grades"
            response = self.client.post(
                "/query",
                json={"question": "Show all students"}
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("sql_query", body)
            self.assertIn("request_id", body)
            self.assertIn("telemetry", body)
            self.assertEqual(body["telemetry"]["attempts"], 1)
            self.assertIn("intent", body["telemetry"])
            mock_run.assert_called_once()

    def test_query_retry_ast_then_success(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "run", return_value="[('Aman',)]"), \
             patch.object(api.db, "get_table_info", return_value="grades(id, name)"):
            mock_chain.invoke.side_effect = [
                "DROP TABLE grades",
                "SELECT name FROM grades",
            ]
            response = self.client.post("/query", json={"question": "show names"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["telemetry"]["attempts"], 2)
            self.assertEqual(mock_chain.invoke.call_count, 2)

    def test_query_retry_db_error_then_success(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id, name)"), \
             patch.object(api.db, "run", side_effect=[Exception("no such column: foo"), "[('Aman',)]"]):
            mock_chain.invoke.side_effect = [
                "SELECT foo FROM grades",
                "SELECT name FROM grades",
            ]
            response = self.client.post("/query", json={"question": "show names"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["telemetry"]["attempts"], 2)

    def test_query_retry_exhausted(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"):
            mock_chain.invoke.return_value = "SELECT * FROM missing_table_xyz"
            with patch.object(api.db, "run", side_effect=Exception("no such table")):
                response = self.client.post("/query", json={"question": "missing"})
                self.assertEqual(response.status_code, 500)
                self.assertEqual(mock_chain.invoke.call_count, 3)

    def test_query_rejects_unsafe(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"):
            mock_chain.invoke.return_value = "DROP TABLE grades"
            response = self.client.post("/query", json={"question": "drop it"})
            self.assertEqual(response.status_code, 400)

    def test_query_rejects_stacked(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"):
            mock_chain.invoke.return_value = "SELECT * FROM grades; DROP TABLE grades"
            response = self.client.post("/query", json={"question": "stacked"})
            self.assertEqual(response.status_code, 400)

    def test_history_validation(self):
        response = self.client.get("/history?limit=-1")
        self.assertEqual(response.status_code, 422)
        response = self.client.get("/history?limit=200")
        self.assertEqual(response.status_code, 422)

    def test_question_validation(self):
        response = self.client.post("/query", json={"question": "   "})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/query", json={"question": ""})
        self.assertEqual(response.status_code, 422)
    
    def test_history(self):
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn("history", response.json())

if __name__ == "__main__":
    unittest.main()
