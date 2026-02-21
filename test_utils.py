import unittest
from utils import clean_sql, is_safe_query

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

if __name__ == "__main__":
    unittest.main()
