"""Operational payload synthesizer (ARCHITECTURE_v2 §4).

Actions are suggestions only — never auto-executed. Approval required.
"""
import ast
import re
from typing import Optional

# Closed taxonomy — no free-form tags
CS_TAGS = {
    "at-risk:math", "at-risk:history", "at-risk:science",
    "praise:grade-A", "praise:grade-B",
    "follow-up:top-performer",
}
GTM_OWNERS = {"csm", "tutor", "sales"}

_AT_RISK = re.compile(r"\b(at risk|low|below|fail|struggling)", re.I)
_TOP = re.compile(r"\b(top|highest|best|excellent|star)\b", re.I)


def _parse_rows(result_repr: str):
    """Parse langchain repr '[(...)]' into list of tuples; None on failure."""
    try:
        val = ast.literal_eval(result_repr)
        if isinstance(val, (list, tuple)):
            return [tuple(r) for r in val if isinstance(r, (list, tuple))]
    except (ValueError, SyntaxError):
        pass
    return None


def _has_low_score(result_repr: str) -> bool:
    rows = _parse_rows(result_repr)
    if rows is None:
        return False
    return any(
        len(r) >= 4 and isinstance(r[3], (int, float)) and r[3] < 70
        for r in rows
    )


def _has_grade_a(result_repr: str) -> bool:
    rows = _parse_rows(result_repr)
    if rows is None:
        return False
    return any(
        len(r) >= 5 and str(r[4]).strip().upper() == "A"
        for r in rows
    )


def synthesize_actions(question: str, sql: str, result_repr: str, intent: str) -> dict:
    """Build email_draft + cs_tags + gtm_triggers from query results.

    Rules (deterministic, no PII beyond what user already queried):
    - aggregate/filter on low scores  -> at-risk:<subject> tag
    - grade A rows                  -> praise:grade-A tag
    - rank intent                   -> follow-up:top-performer
    - at-risk tags                  -> GTM follow-up trigger (owner=csm, 3d)
    - praise tags                   -> GTM kudos trigger (owner=tutor, 7d)
    - every actions set carries needs_approval=true on the email draft
    """
    q = (question or "").lower()

    cs_tags = set()
    if _AT_RISK.search(q) or _has_low_score(result_repr):
        subject = _detect_subject(q, sql)
        cs_tags.add(f"at-risk:{subject}")
    if _has_grade_a(result_repr):
        cs_tags.add("praise:grade-A")
    if intent == "rank" or _TOP.search(q):
        cs_tags.add("follow-up:top-performer")

    gtm_triggers = []
    for tag in sorted(cs_tags):
        if tag.startswith("at-risk:"):
            gtm_triggers.append({
                "type": "follow-up",
                "owner": "csm",
                "due_in_days": 3,
                "reason": f"Student flagged {tag} via query: {question[:80]}",
            })
        elif tag.startswith("praise:"):
            gtm_triggers.append({
                "type": "kudos",
                "owner": "tutor",
                "due_in_days": 7,
                "reason": f"Praise-worthy result for {tag}",
            })
        elif tag == "follow-up:top-performer":
            gtm_triggers.append({
                "type": "recognition",
                "owner": "tutor",
                "due_in_days": 5,
                "reason": "Top performer identified",
            })

    email_draft = None
    if cs_tags:
        first = sorted(cs_tags)[0]
        email_draft = {
            "to_role": "tutor" if first.startswith(("praise", "follow-up")) else "csm",
            "subject": f"Rora AI: {first} flag",
            "body": _draft_body(question, first, sql),
            "needs_approval": True,
        }

    return {
        "email_draft": email_draft,
        "cs_tags": sorted(cs_tags),
        "gtm_triggers": gtm_triggers,
    }


def _detect_subject(question: str, sql: str) -> str:
    for subj in ("math", "history", "science"):
        if subj in question.lower() or subj in sql.lower():
            return subj
    return "math"


def _draft_body(question: str, tag: str, sql: str) -> str:
    return (
        f"Hi,\n\nRora AI flagged '{tag}' from the query:\n"
        f"  Q: {question}\n  SQL: {sql}\n\n"
        f"Review and take action.\n"
    )
