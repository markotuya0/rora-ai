import unittest
from agent import (
    route_intent, prune_schema, trim_error, build_retry_input, MAX_RETRIES,
)


class TestAgent(unittest.TestCase):

    def test_route_intent(self):
        self.assertEqual(route_intent("What is the average score?"), "aggregate")
        self.assertEqual(route_intent("Show top student in Math"), "rank")
        self.assertEqual(route_intent("Show grade A students"), "filter")
        self.assertEqual(route_intent("Show database schema"), "metadata")
        self.assertEqual(route_intent("Group scores by subject"), "trend")

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
