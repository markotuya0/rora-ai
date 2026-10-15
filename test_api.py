import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import api
from api import app

V1 = "/api/v1"


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        api.query_history.clear()
        from rora_api.v1 import routes
        routes._sql_cache.clear()

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("name", body)
        self.assertIn("version", body)
        self.assertEqual(body["status"], "running")

    def test_v1_health(self):
        response = self.client.get(f"{V1}/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_v1_schema(self):
        with patch.object(api.db, "get_table_info", return_value="grades(id, name)"):
            response = self.client.get(f"{V1}/schema")
            self.assertEqual(response.status_code, 200)
            self.assertIn("schema", response.json())

    def test_v1_query_valid(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "run", return_value="[(1, 'Aman')]"), \
             patch.object(api.db, "get_table_info", return_value="grades(id, name)"):
            mock_chain.invoke.return_value = "SELECT * FROM grades"
            response = self.client.post(f"{V1}/query", json={"question": "Show all students"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertIn("sql_query", body)
            self.assertIn("request_id", body)
            self.assertIn("telemetry", body)
            self.assertEqual(body["telemetry"]["attempts"], 1)
            self.assertIn("intent", body["telemetry"])

    def test_v1_query_rejects_unsafe(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"):
            mock_chain.invoke.return_value = "DROP TABLE grades"
            response = self.client.post(f"{V1}/query", json={"question": "drop it"})
            self.assertEqual(response.status_code, 400)
            body = response.json()
            self.assertIn("error", body)
            self.assertEqual(body["error"]["code"], "UNSAFE_SQL")
            self.assertIn("requestId", body["error"])

    def test_v1_query_retry_ast_then_success(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "run", return_value="[('Aman',)]"), \
             patch.object(api.db, "get_table_info", return_value="grades(id, name)"):
            mock_chain.invoke.side_effect = ["DROP TABLE grades", "SELECT name FROM grades"]
            response = self.client.post(f"{V1}/query", json={"question": "show names"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["telemetry"]["attempts"], 2)

    def test_v1_query_retry_exhausted(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"), \
             patch.object(api.db, "run", side_effect=Exception("no such table")):
            mock_chain.invoke.return_value = "SELECT * FROM grades"
            response = self.client.post(f"{V1}/query", json={"question": "missing"})
            self.assertEqual(response.status_code, 500)
            self.assertEqual(mock_chain.invoke.call_count, 3)

    def test_v1_query_out_of_scope_fails_fast(self):
        # Churn data does not exist in the demo DB: reject before any LLM call.
        with patch.object(api, "sql_chain") as mock_chain:
            response = self.client.post(f"{V1}/query", json={"question": "which customer churned the last time"})
            self.assertEqual(response.status_code, 422)
            self.assertIn("student grades", response.json()["error"]["message"])
            mock_chain.invoke.assert_not_called()

    def test_v1_query_retries_when_subject_filter_missing(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id, name, subject, score)"), \
             patch.object(api.db, "run", return_value="[('Aman', 95)]"):
            mock_chain.invoke.side_effect = [
                "SELECT name FROM grades ORDER BY score DESC LIMIT 3",
                "SELECT name FROM grades WHERE subject = 'Math' ORDER BY score DESC LIMIT 3",
            ]
            response = self.client.post(f"{V1}/query", json={"question": "show the top three students in Math"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_chain.invoke.call_count, 2)
            self.assertIn("'Math'", response.json()["sql_query"])
            self.assertEqual(response.json()["telemetry"]["attempts"], 2)

    def test_config_reports_demo_mode_and_examples(self):
        with patch.object(api.db, "get_table_info", return_value="CREATE TABLE grades (id INT)"):
            body = self.client.get(f"{V1}/config").json()
        self.assertTrue(body["demo_mode"])
        self.assertEqual(body["tables"], ["grades"])
        self.assertIn("Average score per subject", body["examples"])

    def test_live_mode_skips_demo_scope_and_examples(self):
        from rora_api.v1 import routes
        with patch.object(routes, "DEMO_MODE", False), \
             patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="CREATE TABLE customers (id INT, churned INT)"), \
             patch.object(api.db, "run", return_value="[(1,)]"):
            mock_chain.invoke.return_value = "SELECT COUNT(*) FROM customers WHERE churned = 1"
            response = self.client.post(f"{V1}/query", json={"question": "which customer churned the last time"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["telemetry"]["tables"], ["customers"])
        with patch.object(routes, "DEMO_MODE", False), \
             patch.object(api.db, "get_table_info", return_value="CREATE TABLE customers (id INT)"):
            self.assertEqual(self.client.get(f"{V1}/config").json()["examples"], [])

    def test_saved_example_skips_model(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="CREATE TABLE grades (id INT, name TEXT, subject TEXT, score INT, grade TEXT)"), \
             patch.object(api.db, "run", return_value="[(90.0, 'History')]"):
            response = self.client.post(f"{V1}/query", json={"question": "Average score per subject?"})
            self.assertEqual(response.status_code, 200)
            mock_chain.invoke.assert_not_called()
            self.assertEqual(response.json()["telemetry"]["source"], "example")

    def test_repeated_question_is_served_from_cache(self):
        schema = "CREATE TABLE grades (id INT, name TEXT, subject TEXT, score INT, grade TEXT)"
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value=schema), \
             patch.object(api.db, "run", return_value="[('Aman',)]"):
            mock_chain.invoke.return_value = "SELECT name FROM grades WHERE grade = 'A'"
            first = self.client.post(f"{V1}/query", json={"question": "who got an A"}).json()
            second = self.client.post(f"{V1}/query", json={"question": "who got an A"}).json()
            self.assertEqual(mock_chain.invoke.call_count, 1)
            self.assertEqual(first["telemetry"]["source"], "model")
            self.assertEqual(second["telemetry"]["source"], "cache")
            self.assertEqual(second["sql_query"], first["sql_query"])

    def test_failing_cached_sql_is_evicted_and_model_takes_over(self):
        schema = "CREATE TABLE grades (id INT, name TEXT, subject TEXT, score INT, grade TEXT)"
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value=schema), \
             patch.object(api.db, "run", return_value="[('Aman',)]"):
            mock_chain.invoke.return_value = "SELECT name FROM grades WHERE grade = 'A'"
            self.client.post(f"{V1}/query", json={"question": "who got an A"})
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value=schema), \
             patch.object(api.db, "run", side_effect=[Exception("no such column: grade_x"), "[('Aman',)]"]):
            mock_chain.invoke.return_value = "SELECT name FROM grades WHERE grade = 'A'"
            body = self.client.post(f"{V1}/query", json={"question": "who got an A"}).json()
            self.assertEqual(mock_chain.invoke.call_count, 1)
            self.assertEqual(body["telemetry"]["source"], "model")
            self.assertEqual(body["telemetry"]["attempts"], 2)

    def test_sample_profiles_connected_database(self):
        with patch.object(api.db, "profile", return_value={"tables": [{"name": "customers", "rows": 3}]}) as prof:
            body = self.client.get(f"{V1}/sample?rows=2").json()
        prof.assert_called_once_with(2)
        self.assertEqual(body["tables"][0]["name"], "customers")
        self.assertIn("demo_mode", body)

    def test_v1_query_retry_exhausted_reports_db_error(self):
        with patch.object(api, "sql_chain") as mock_chain, \
             patch.object(api.db, "get_table_info", return_value="grades(id)"), \
             patch.object(api.db, "run", side_effect=Exception("no such column: churned")):
            mock_chain.invoke.return_value = "SELECT churned FROM grades"
            response = self.client.post(f"{V1}/query", json={"question": "show names"})
            self.assertEqual(response.status_code, 500)
            self.assertIn("no such column: churned", response.json()["error"]["message"])

    def test_v1_history_cursor(self):
        api.query_history.extend([{"q": "a"}, {"q": "b"}, {"q": "c"}])
        response = self.client.get(f"{V1}/history?limit=2")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(len(body["items"]), 2)
        self.assertIsNotNone(body["next_cursor"])
        response2 = self.client.get(f"{V1}/history?limit=2&cursor={body['next_cursor']}")
        self.assertEqual(len(response2.json()["items"]), 1)
        self.assertIsNone(response2.json()["next_cursor"])

    def test_v1_history_validation(self):
        self.assertEqual(self.client.get(f"{V1}/history?limit=-1").status_code, 422)
        self.assertEqual(self.client.get(f"{V1}/history?limit=200").status_code, 422)

    def test_v1_question_validation(self):
        self.assertEqual(self.client.post(f"{V1}/query", json={"question": "   "}).status_code, 422)
        self.assertEqual(self.client.post(f"{V1}/query", json={"question": ""}).status_code, 422)
        err = self.client.post(f"{V1}/query", json={"question": "   "}).json()
        self.assertEqual(err["error"]["code"], "VALIDATION_ERROR")

    def test_legacy_redirects_308(self):
        self.assertEqual(self.client.get("/query", follow_redirects=False).status_code, 308)
        self.assertEqual(self.client.post("/query", json={"question": "x"}, follow_redirects=False).status_code, 308)
        self.assertEqual(self.client.get("/history", follow_redirects=False).status_code, 308)
        self.assertEqual(self.client.get("/schema", follow_redirects=False).status_code, 308)
        self.assertEqual(self.client.get("/health", follow_redirects=False).status_code, 308)

    def test_rate_limit_enforced(self):
        from rora_api.core import rate_limit
        old_limit = rate_limit.RATE_LIMIT
        rate_limit.RATE_LIMIT = 3
        rate_limit._hits.clear()
        try:
            for _ in range(3):
                self.assertEqual(self.client.get(f"{V1}/schema").status_code, 200)
            response = self.client.get(f"{V1}/schema")
            self.assertEqual(response.status_code, 429)
            self.assertIn("Retry-After", response.headers)
        finally:
            rate_limit.RATE_LIMIT = old_limit
            rate_limit._hits.clear()

    def test_jwt_scaffold_blocks_when_enabled(self):
        from rora_api.core import auth
        auth.AUTH_ENABLED = True
        auth.AUTH_SECRET = "test-secret"
        try:
            resp = self.client.get(f"{V1}/schema")
            self.assertEqual(resp.status_code, 403)
            token = auth.create_token("dev", ["read:query"])
            resp = self.client.get(f"{V1}/schema", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(resp.status_code, 200)
        finally:
            auth.AUTH_ENABLED = False
            auth.AUTH_SECRET = "dev-secret-change-me"


if __name__ == "__main__":
    unittest.main()
