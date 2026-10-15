"""Pagination helpers (api-design-reviewer: cursor-based for /history, capped limit/offset)."""
import base64
import json
from typing import Optional


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def decode_cursor(cursor: Optional[str]) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        return max(0, int(json.loads(base64.urlsafe_b64decode(padded).decode()).get("o", 0)))
    except Exception:
        return 0


def paginated(history: list, limit: int, cursor: Optional[str] = None):
    """Cursor-paginate history list. Returns {items, next_cursor, total}."""
    offset = decode_cursor(cursor)
    items = history[offset: offset + limit]
    next_offset = offset + len(items)
    next_cursor = encode_cursor(next_offset) if next_offset < len(history) else None
    return {"items": items, "next_cursor": next_cursor, "total": len(history)}
