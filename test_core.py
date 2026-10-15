import unittest
from rora_api.core.pagination import encode_cursor, decode_cursor, paginated
from rora_api.core.auth import create_token, verify_token, require_scope
from rora_api.core.envelope import envelope_body


class TestPagination(unittest.TestCase):

    def test_cursor_roundtrip(self):
        c = encode_cursor(42)
        self.assertEqual(decode_cursor(c), 42)

    def test_cursor_invalid_returns_zero(self):
        self.assertEqual(decode_cursor("not-a-cursor!!"), 0)
        self.assertEqual(decode_cursor(None), 0)

    def test_paginated_items_and_next(self):
        history = [{"q": f"q{i}"} for i in range(5)]
        page1 = paginated(history, 2)
        self.assertEqual(len(page1["items"]), 2)
        self.assertIsNotNone(page1["next_cursor"])
        page2 = paginated(history, 2, page1["next_cursor"])
        self.assertEqual(page2["items"][0]["q"], "q2")
        last = paginated(history, 2, paginated(history, 4)["next_cursor"])
        self.assertEqual(last["total"], 5)


class TestAuth(unittest.TestCase):

    def test_token_roundtrip(self):
        token = create_token("dev", ["read:query"])
        claims = verify_token(token)
        self.assertEqual(claims["sub"], "dev")
        self.assertIn("read:query", claims["scopes"])

    def test_token_tampered_rejected(self):
        token = create_token("dev", ["read:query"])
        self.assertIsNone(verify_token(token + "x"))

    def test_scope_check_disabled_by_default(self):
        self.assertTrue(require_scope(None, "read:query"))

    def test_scope_check_enabled(self):
        from rora_api.core import auth
        auth.AUTH_ENABLED = True
        auth.AUTH_SECRET = "s3cret"
        try:
            token = create_token("dev", ["read:query"])
            claims = verify_token(token)
            self.assertTrue(require_scope(claims, "read:query"))
            self.assertFalse(require_scope(claims, "approve:action"))
            self.assertFalse(require_scope(None, "read:query"))
        finally:
            auth.AUTH_ENABLED = False
            auth.AUTH_SECRET = "dev-secret-change-me"


class TestErrorEnvelope(unittest.TestCase):

    def test_envelope_shape(self):
        body = envelope_body("VALIDATION_ERROR", "bad", details=[{"field": "question"}])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("requestId", body["error"])
        self.assertIn("timestamp", body["error"])
        self.assertEqual(body["error"]["details"][0]["field"], "question")


if __name__ == "__main__":
    unittest.main()
