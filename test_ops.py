import unittest
from ops.payloads import synthesize_actions, CS_TAGS
from ops.audit import log_event, recent_events, _events


class TestPayloads(unittest.TestCase):

    def test_at_risk_tag_and_trigger(self):
        a = synthesize_actions("Show failing Math students", "SELECT * FROM grades WHERE subject='Math' AND score<70",
                               "[(6, 'Nandini', 'Math', 65, 'D')]", "filter")
        self.assertIn("at-risk:math", a["cs_tags"])
        self.assertTrue(any(t["owner"] == "csm" and t["due_in_days"] == 3 for t in a["gtm_triggers"]))

    def test_praise_tag(self):
        a = synthesize_actions("Show top Math student", "SELECT * FROM grades ORDER BY score DESC",
                               "[(1, 'Aman', 'Math', 95, 'A')]", "rank")
        self.assertIn("praise:grade-A", a["cs_tags"])
        self.assertIn("follow-up:top-performer", a["cs_tags"])
        self.assertTrue(any(t["type"] == "recognition" for t in a["gtm_triggers"]))

    def test_email_draft_requires_approval(self):
        a = synthesize_actions("Show failing students", "SELECT * FROM grades", "[(1,'X','Math',50,'F')]", "filter")
        self.assertIsNotNone(a["email_draft"])
        self.assertTrue(a["email_draft"]["needs_approval"])
        self.assertIn("to_role", a["email_draft"])

    def test_tags_closed_taxonomy(self):
        a = synthesize_actions("hello", "SELECT 1", "[]", "filter")
        for tag in a["cs_tags"]:
            self.assertIn(tag, CS_TAGS)

    def test_no_actions_for_empty(self):
        a = synthesize_actions("metadata", "SELECT 1", "[]", "metadata")
        self.assertEqual(a["cs_tags"], [])
        self.assertIsNone(a["email_draft"])


class TestAudit(unittest.TestCase):

    def test_log_event_appends(self):
        before = len(_events)
        log_event("test", {"x": 1}, actor="tester", request_id="req-test")
        self.assertEqual(len(_events), before + 1)
        self.assertEqual(recent_events(1)[0]["event"], "test")
        self.assertEqual(recent_events(1)[0]["actor"], "tester")


if __name__ == "__main__":
    unittest.main()
