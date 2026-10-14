"""Sliding-window rate limiter (in-memory, per-client). 429 + Retry-After per matrix."""
import os
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
_WINDOW = 60.0
_hits: dict = defaultdict(deque)


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()


def check_rate_limit(request: Request):
    now = time.time()
    key = _client_key(request)
    q = _hits[key]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        retry_after = int(_WINDOW - (now - q[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(RATE_LIMIT), "X-RateLimit-Remaining": "0"},
        )
    q.append(now)
    return RATE_LIMIT - len(q)
