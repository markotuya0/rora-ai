"""Audit log for operational actions (append-only JSONL, no PII)."""
import json
import os
from datetime import datetime, timezone
from typing import Optional

AUDIT_PATH = os.getenv("AUDIT_LOG_PATH", "audit.jsonl")
_events: list = []  # in-memory mirror for tests/UI


def log_event(event_type: str, payload: dict, actor: str = "system", request_id: Optional[str] = None) -> dict:
    entry = {
        "event": event_type,
        "actor": actor,
        "request_id": request_id,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _events.append(entry)
    try:
        os.makedirs(os.path.dirname(AUDIT_PATH) or ".", exist_ok=True)
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # fail-open: memory mirror still works
    return entry


def recent_events(limit: int = 100) -> list:
    return list(reversed(_events[-limit:]))
