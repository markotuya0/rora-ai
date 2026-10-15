"""Standard error envelope — pure builder (stdlib-only, testable offline)."""
import uuid
from datetime import datetime, timezone


def envelope_body(code: str, message: str, details=None, request_id: str = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "requestId": request_id or f"req-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


def build_envelope(code: str, message: str, status_code: int, details=None, request_id: str = None) -> tuple:
    """Returns (body_dict, status_code)."""
    return envelope_body(code, message, details, request_id), status_code
