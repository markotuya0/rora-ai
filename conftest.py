"""Pytest bootstrap: point the DB at a throwaway file before any app module imports config.

test_db.py drops every table in teardown, so tests must never touch the real demo database.
"""
import os

os.environ["DB_PATH"] = "test_student_grades.db"
