"""Officer login: one demo account from env vars, stateless signed tokens (no session table, nothing to leak).

The account comes from the server's environment settings. If no password is configured, nobody can sign in.
Tokens are signed with a value derived from that configuration, so changing it signs everyone out."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

DEFAULT_USER = "officer"


def _creds() -> tuple[str, str]:
    return os.getenv("OFFICER_USER", DEFAULT_USER), os.getenv("OFFICER_PASSWORD", "")


def _secret() -> bytes:
    return (os.getenv("AUTH_SECRET") or (_creds()[1] + "|seva-agent")).encode()


def check_login(user: str, password: str) -> bool:
    u, p = _creds()
    if not p:  # nothing configured: refuse everyone
        return False
    return hmac.compare_digest(user.encode(), u.encode()) & hmac.compare_digest(password.encode(), p.encode())


def make_token(user: str, ttl: int = 12 * 3600) -> str:
    payload = f"{user}|{int(time.time()) + ttl}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def verify_token(token: str) -> str | None:
    try:
        user, exp, sig = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
    except Exception:
        return None
    good = hmac.new(_secret(), f"{user}|{exp}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good) or int(exp) < time.time():
        return None
    return user
