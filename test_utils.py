import unittest
from utils import clean_sql, is_safe_query, validate_sql, ensure_limit

class TestUtils(unittest.TestCase):
    
    def test_clean_sql_with_markdown(self):
        input_sql = "```sql\nSELECT * FROM grades\n```"
        expected = "SELECT * FROM grades"
        self.assertEqual(clean_sql(input_sql), expected)
    
    def test_clean_sql_without_markdown(self):
        input_sql = "SELECT * FROM grades"
        self.assertEqual(clean_sql(input_sql), input_sql)
    
    def test_is_safe_query_select(self):
        self.assertTrue(is_safe_query("SELECT * FROM grades"))
        self.assertTrue(is_safe_query("  select name from grades"))
    
    def test_is_safe_query_unsafe(self):
        self.assertFalse(is_safe_query("DROP TABLE grades"))
        self.assertFalse(is_safe_query("INSERT INTO grades VALUES (1, 'test')"))
        self.assertFalse(is_safe_query("UPDATE grades SET score = 100"))

    def test_ast_rejects_stacked_statements(self):
        self.assertFalse(is_safe_query("SELECT * FROM grades; DROP TABLE grades"))

    def test_ast_rejects_comments(self):
        self.assertFalse(is_safe_query("SELECT * FROM grades -- drop"))
        self.assertFalse(is_safe_query("SELECT * FROM grades /* comment */"))

    def test_ast_allows_join_select(self):
        self.assertTrue(is_safe_query("SELECT a.name, b.score FROM grades a JOIN grades b ON a.id = b.id"))

    def test_ensure_limit_injects(self):
        out = ensure_limit("SELECT * FROM grades")
        self.assertIn("LIMIT", out.upper())

    def test_ensure_limit_clamps(self):
        out = ensure_limit("SELECT * FROM grades LIMIT 5000", max_limit=1000)
        self.assertIn("1000", out)
        self.assertNotIn("5000", out)

    def test_validate_sql_reason(self):
        ok, reason, tables = validate_sql("DROP TABLE grades")
        self.assertFalse(ok)
        self.assertTrue(reason)

if __name__ == "__main__":
    unittest.main()
