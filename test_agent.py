import unittest
from agent import (
    route_intent, prune_schema, trim_error, build_retry_input, is_in_scope, missing_subject_filters, prune_live_schema, normalize_question, saved_sql, MAX_RETRIES,
)


class TestAgent(unittest.TestCase):

    def test_route_intent(self):
        self.assertEqual(route_intent("What is the average score?"), "aggregate")
        self.assertEqual(route_intent("Show top student in Math"), "rank")
        self.assertEqual(route_intent("Show grade A students"), "filter")
        self.assertEqual(route_intent("Show database schema"), "metadata")
        self.assertEqual(route_intent("Group scores by subject"), "trend")

    def test_is_in_scope(self):
        self.assertFalse(is_in_scope("which customer churned the last time"))
        self.assertFalse(is_in_scope("list all orders"))
        self.assertTrue(is_in_scope("average score per subject"))
        self.assertTrue(is_in_scope("Rahul's score"))
        self.assertTrue(is_in_scope("show database schema"))
        self.assertTrue(is_in_scope("order by score"))  # in-domain term wins

    def test_missing_subject_filters(self):
        self.assertEqual(missing_subject_filters("top 3 students in Math", "SELECT name FROM grades ORDER BY score DESC LIMIT 3"), ["Math"])
        self.assertEqual(missing_subject_filters("top 3 students in Math", "SELECT name FROM grades WHERE subject = 'Math'"), [])
        self.assertEqual(missing_subject_filters("average score per subject", "SELECT AVG(score) FROM grades"), [])
        self.assertEqual(missing_subject_filters("compare Math and History", "SELECT * FROM grades WHERE subject = 'Math'"), ["History"])

    def test_prune_live_schema_keeps_named_table(self):
        schema = "CREATE TABLE customers (id INT, churned INT)\n\nCREATE TABLE orders (id INT, total REAL)"
        p = prune_live_schema(schema, "which customers churned", {"customers", "orders"})
        self.assertIn("customers", p["pruned_schema"])
        self.assertNotIn("orders", p["pruned_schema"])
        self.assertEqual(p["tables_kept"], ["customers"])

    def test_prune_live_schema_falls_back_to_full_schema(self):
        schema = "CREATE TABLE customers (id INT)\n\nCREATE TABLE orders (id INT)"
        p = prune_live_schema(schema, "how many rows in total", {"customers", "orders"})
        self.assertEqual(p["pruned_schema"], schema)

    def test_prune_live_schema_postgres_lines(self):
        schema = "customers.id (integer)\ncustomers.churned (boolean)\norders.total (numeric)"
        p = prune_live_schema(schema, "customers who churned", {"customers", "orders"})
        self.assertEqual(p["pruned_schema"], "customers.id (integer)\ncustomers.churned (boolean)")

    def test_saved_sql_matches_normalized_example(self):
        self.assertEqual(normalize_question("Who scored below 70?"), "who scored below 70")
        self.assertIn("score < 70", saved_sql("who scored below 70 ?"))
        self.assertIsNone(saved_sql("which customer churned"))

    def test_prune_schema_keeps_relevant(self):
        full = "CREATE TABLE grades (id INT, name TEXT, subject TEXT, score INT, grade TEXT)"
        p = prune_schema(full, "average score in Math", "aggregate")
        self.assertIn("grades", p["tables_kept"])
        self.assertIn("score", p["columns_kept"])
        self.assertLess(p["tokens_pruned_est"], p["tokens_full_est"])
        self.assertGreater(p["reduction_pct"], 0)

    def test_prune_schema_filter_default(self):
        p = prune_schema("grades(id, name, subject, score, grade)", "hello", "filter")
        self.assertTrue(len(p["columns_kept"]) >= 1)

    def test_trim_error_drops_sql_dump(self):
        err = "(sqlite3.OperationalError) near \"group\": syntax error\n[SQL: SELECT * FROM grades GROUP]"
        self.assertEqual(trim_error(err), '(sqlite3.OperationalError) near "group": syntax error')

    def test_trim_error_truncates_and_redacts(self):
        long_err = "x" * 500
        self.assertLessEqual(len(trim_error(long_err)), 300)
        self.assertIn("***", trim_error("password = supersecret123"))

    def test_retry_input_contains_feedback(self):
        d = build_retry_input("Show all", "grades(name)", "DROP TABLE x", "forbidden")
        self.assertIn("DROP TABLE x", d["question"])
        self.assertIn("forbidden", d["question"])

    def test_max_retries_cap(self):
        self.assertEqual(MAX_RETRIES, 2)


if __name__ == "__main__":
    unittest.main()
