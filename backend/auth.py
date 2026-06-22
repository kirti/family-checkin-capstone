"""
auth.py

Simple but real session-based auth, appropriate for a small personal
tool with one shared login (not a multi-user system, so no user table
or password hashing needed - the single username/password pair lives
entirely in environment variables, compared with a constant-time check).

Key design point: protection happens at the API level (require_auth
decorator on the actual endpoints), not just on the frontend pages -
so someone can't bypass the login screen by calling the API directly.
"""

import os
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import request, jsonify

from db_tools import get_conn

SESSION_LIFETIME_DAYS = 7
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def init_auth_tables() -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id SERIAL PRIMARY KEY,
                    attempted_at TEXT NOT NULL,
                    success BOOLEAN NOT NULL
                )
            """)
        conn.commit()
    finally:
        conn.close()


def _too_many_recent_failures() -> bool:
    cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)).isoformat()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE success = FALSE AND attempted_at > %s",
                (cutoff,),
            )
            count = cur.fetchone()[0]
    finally:
        conn.close()
    return count >= MAX_FAILED_ATTEMPTS


def _record_attempt(success: bool) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO login_attempts (attempted_at, success) VALUES (%s, %s)",
                (datetime.now().isoformat(), success),
            )
        conn.commit()
    finally:
        conn.close()


def attempt_login(username: str, password: str) -> str | None:
    """Returns a new session token if credentials are correct, else None.
    Returns None (treated as failure) if locked out from too many recent
    failed attempts, regardless of whether these credentials are correct."""
    if _too_many_recent_failures():
        return None

    expected_username = os.environ.get("SITE_LOGIN_USERNAME", "")
    expected_password = os.environ.get("SITE_LOGIN_PASSWORD", "")

    # Constant-time comparison - resists timing-based guessing attacks.
    username_ok = hmac.compare_digest(username, expected_username)
    password_ok = hmac.compare_digest(password, expected_password)

    if not (username_ok and password_ok):
        _record_attempt(success=False)
        return None

    _record_attempt(success=True)

    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(days=SESSION_LIFETIME_DAYS)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, created_at, expires_at) VALUES (%s, %s, %s)",
                (token, now.isoformat(), expires.isoformat()),
            )
        conn.commit()
    finally:
        conn.close()

    return token


def _is_valid_token(token: str) -> bool:
    if not token:
        return False

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT expires_at FROM sessions WHERE token = %s", (token,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return False

    expires_at = datetime.fromisoformat(row[0])
    return datetime.now() < expires_at


def require_auth(view_func):
    """Decorator: protects an endpoint so it only works with a valid
    session token in the Authorization header, e.g.:
    Authorization: Bearer <token>"""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

        if not _is_valid_token(token):
            return jsonify({"error": "Unauthorized"}), 401

        return view_func(*args, **kwargs)

    return wrapped
