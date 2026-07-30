"""Password hashing and server-side session helpers for Part 11 (auth foundation).

Sessions are opaque, DB-backed tokens (not JWTs) so logout is a real, immediate
revocation rather than needing a blocklist. A flat expiry with no sliding
renewal and no login rate-limiting/lockout are deliberate simplifications for
this local, single-container MVP.
"""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from . import db

SESSION_COOKIE_NAME = "pm_session"
SESSION_TTL_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/legacy hash that bcrypt can't parse - treat as no match.
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def create_session(connection: sqlite3.Connection, user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=SESSION_TTL_DAYS)
    db.insert_session(connection, token, user_id, _format_timestamp(expires_at))
    return token, expires_at


def get_session_user(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    """Return ``{"user_id": int, "username": str}`` for a valid, unexpired session token."""
    if not token:
        return None

    session = db.get_session_with_user(connection, token)
    if session is None:
        return None

    if _parse_timestamp(session["expires_at"]) <= _now():
        return None

    return {"user_id": session["user_id"], "username": session["username"]}


def delete_session(connection: sqlite3.Connection, token: str) -> None:
    db.delete_session(connection, token)
