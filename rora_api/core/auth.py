"""JWT auth scaffold (single-tenant bearer, RBAC scopes).

Disabled by default: AUTH_ENABLED=false keeps dev/tests frictionless.
Enable by setting AUTH_SECRET + AUTH_ENABLED=true.
"""
import os
import hmac
import hashlib
import base64
import json
import time
from typing import Optional

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", "3600"))
_ISSUER = "rora-ai"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(subject: str, scopes: list) -> str:
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64e(json.dumps({
        "sub": subject,
        "scopes": scopes,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL,
        "iss": _ISSUER,
    }).encode())
    sig = _b64e(hmac.new(AUTH_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    try:
        header, payload, sig = token.split(".")
        expected = hmac.new(AUTH_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64e(expected), sig):
            return None
        claims = json.loads(_b64d(payload))
        if claims.get("exp", 0) < time.time():
            return None
        return claims
    except Exception:
        return None


def require_scope(claims: Optional[dict], scope: str) -> bool:
    if not AUTH_ENABLED:
        return True
    if not claims:
        return False
    return scope in claims.get("scopes", [])
