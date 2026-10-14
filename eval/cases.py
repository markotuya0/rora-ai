"""The 20 regression cases (ARCHITECTURE_v2 §6).

Each case: (id, question, expect_sql_substring | None, expect_status).
Kept deterministic — run against mocked chain/db in pytest.
"""
CASES = [
    # --- 9 kept from original suite (fixed) ---
    ("c01_root", "Show all students", None, 200),
    ("c02_health", "ping", None, 200),          # health endpoint (question unused)
    ("c03_schema", "describe schema", None, 200),  # schema endpoint
    ("c04_query_valid", "Show all students", "SELECT", 200),
    ("c05_history", "history", None, 200),      # history endpoint
    ("c06_clean_fence", "```sql\nSELECT * FROM grades\n```", "SELECT", 200),
    ("c07_clean_plain", "SELECT * FROM grades", "SELECT", 200),
    ("c08_safe_select", "SELECT * FROM grades", True, 200),   # is_safe_query True
    ("c09_safe_unsafe", "DROP TABLE grades", False, 400),     # is_safe_query False

    # --- 11 new (Phase 6) ---
    ("c10_stacked", "x; DROP TABLE grades", None, 400),
    ("c11_union_exfil", "SELECT * FROM grades UNION SELECT * FROM secrets", None, 400),
    ("c12_multi_statement", "SELECT 1; SELECT 2", None, 400),
    ("c13_limit_injected", "SELECT * FROM grades", "LIMIT", 200),
    ("c14_retry_unknown_column", "SELECT * FROM grades", "SELECT", 200),  # pass-2 success
    ("c15_retry_db_error", "SELECT * FROM grades", "SELECT", 200),        # PG-error retry
    ("c16_retry_exhausted", "SELECT * FROM grades", None, 500),
    ("c17_history_limit_neg", "history", None, 422),
    ("c18_question_oversized", "x" * 600, None, 422),
    ("c19_empty_db_result", "SELECT * FROM grades", "SELECT", 200),       # empty valid + actions
    ("c20_telemetry_fields", "Show all students", "telemetry", 200),
]
