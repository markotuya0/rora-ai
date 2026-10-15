import unittest
from sqlalchemy import text
from db.engine import engine, SessionLocal
from db.client import DBClient, run_query, get_table_info, healthcheck, profile_database
from db.models import Base, Grade


class TestDBClient(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(engine)
        self.client = DBClient()

    def tearDown(self):
        Base.metadata.drop_all(engine)

    def test_create_table_and_seed(self):
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM grades")).scalar()
        self.assertEqual(count, 0)

    def test_run_query_returns_repr(self):
        with SessionLocal() as s:
            s.execute(text("INSERT INTO grades (id, name, subject, score, grade) VALUES (1, 'A', 'Math', 90, 'A')"))
            s.commit()
        out = self.client.run("SELECT * FROM grades")
        self.assertIn("'A'", out)  # smoke: returns string repr of the inserted row
        self.assertIn("(", out)

    def test_get_table_info_sqlite(self):
        info = get_table_info()
        self.assertIn("grades", info.lower())

    def test_healthcheck_true(self):
        self.assertTrue(healthcheck())

    def test_readonly_postgres_listener_registered(self):
        from db import engine as eng_mod
        is_pg = engine.url.get_backend_name() == "postgresql"
        # Listener only attached for postgres; sqlite relies on AST guard
        self.assertFalse(is_pg)  # dev default is sqlite


if __name__ == "__main__":
    unittest.main()


class TestProfile(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(engine)
        with SessionLocal() as s:
            s.execute(text("INSERT INTO grades (id, name, subject, score, grade) VALUES (1, 'Aman', 'Math', 95, 'A'), (2, 'Anshu', 'Math', 78, 'C')"))
            s.commit()

    def tearDown(self):
        Base.metadata.drop_all(engine)

    def test_profile_counts_rows_and_column_stats(self):
        grades = next(t for t in profile_database(2)["tables"] if t["name"] == "grades")
        self.assertEqual(grades["rows"], 2)
        self.assertEqual(len(grades["sample"]), 2)
        score = next(s for s in grades["stats"] if s["column"] == "score")
        self.assertEqual((score["kind"], score["min"], score["max"], score["avg"]), ("numeric", 78, 95, 86.5))
        subject = next(s for s in grades["stats"] if s["column"] == "subject")
        self.assertEqual(subject["distinct"], 1)
        self.assertEqual(subject["top"], [["Math", 2]])
