"""PostgreSQL-backed login sessions, without a SESSION_SECRET/signing key.

The browser stores only an unpredictable, HttpOnly session identifier.
The PostgreSQL table stores its SHA-256 hash and server-side session data.
This is intended for the existing local FastAPI classroom application.
"""

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from database import get_connection

COOKIE_NAME = "pudding_sid"
SESSION_SECONDS = 7 * 24 * 60 * 60


def ensure_session_table():
    """Create the additional table if it is not already present."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS web_sessions (
                    token_hash VARCHAR(64) PRIMARY KEY,
                    session_data JSONB NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL
                )
            """)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _load_session(token: str | None):
    """Return (session dict, valid_cookie). Missing/expired tokens are guests."""
    if not token or len(token) > 128:
        return {}, False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_data FROM web_sessions "
                "WHERE token_hash = %s AND expires_at > NOW()",
                (_token_hash(token),),
            )
            result = cur.fetchone()
            if result is None:
                return {}, False

            data = result[0]
            if isinstance(data, str):
                data = json.loads(data)
            data = dict(data)

            # Role/username must reflect the current users table, not a stale copy.
            user_id = data.get("user_id")
            if user_id is not None:
                cur.execute(
                    "SELECT username, role FROM users WHERE id = %s",
                    (user_id,),
                )
                user = cur.fetchone()
                if user is None:
                    data.pop("user_id", None)
                    data.pop("username", None)
                    data.pop("role", None)
                else:
                    data["username"], data["role"] = user
            return data, True


def _save_session(token: str, data: dict):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO web_sessions (token_hash, session_data, expires_at)
                   VALUES (%s, %s::jsonb, %s)
                   ON CONFLICT (token_hash)
                   DO UPDATE SET session_data = EXCLUDED.session_data,
                                 expires_at = EXCLUDED.expires_at""",
                (_token_hash(token), json.dumps(data), expires_at),
            )


def _delete_session(token: str | None):
    if not token or len(token) > 128:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM web_sessions WHERE token_hash = %s",
                (_token_hash(token),),
            )


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        existing_token = request.cookies.get(COOKIE_NAME)
        session, valid_cookie = _load_session(existing_token)
        previous = dict(session)

        # Keep request.session available to the existing main.py and Jinja2 HTML.
        request.scope["session"] = session
        response = await call_next(request)
        current = request.scope["session"]

        if not current:
            # Logout: revoke on the server, not just in the browser.
            if valid_cookie:
                _delete_session(existing_token)
            if existing_token:
                response.delete_cookie(COOKIE_NAME, path="/")
        elif current != previous or not valid_cookie:
            # Rotate token on login to prevent session fixation.
            logged_in_now = (bool(current.get("user_id"))
                             and previous.get("user_id") != current.get("user_id"))
            if valid_cookie and logged_in_now:
                _delete_session(existing_token)
            token = existing_token if valid_cookie and not logged_in_now else secrets.token_urlsafe(32)
            _save_session(token, current)
            response.set_cookie(
                COOKIE_NAME,
                token,
                max_age=SESSION_SECONDS,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
                path="/",
            )
        return response
