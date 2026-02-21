import unittest
from fastapi.testclient import TestClient
from api import app

class TestAPI(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
    
    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
    
    def test_schema(self):
        response = self.client.get("/schema")
        self.assertEqual(response.status_code, 200)
        self.assertIn("schema", response.json())
    
    def test_query_valid(self):
        response = self.client.post(
            "/query",
            json={"question": "Show all students"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("sql_query", response.json())
    
    def test_history(self):
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn("history", response.json())

if __name__ == "__main__":
    unittest.main()
