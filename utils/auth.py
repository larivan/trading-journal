# utils/auth.py — Authentication helpers (bcrypt + session_state + cookie sessions)
from __future__ import annotations

import hashlib
import hmac as _hmac
import os
import time
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as _components

try:
    import bcrypt as _bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

from db.users import get_user_by_username, get_user_settings, create_user, count_users

# ---------------------------------------------------------------------------
# Cookie-based session persistence
# ---------------------------------------------------------------------------
_SESSION_COOKIE = "tj_session"
_SESSION_SECRET = os.environ.get("TJ_SECRET_KEY", "tj-default-secret-please-change")
_SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days


def _sign_token(user_id: int) -> str:
    """Create a signed session token: '<user_id>:<ts>:<hmac>'."""
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = _hmac.new(
        _SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}:{sig}"


def _verify_token(token: str) -> Optional[int]:
    """Verify signature and expiry. Return user_id or None."""
    try:
        # token = "user_id:ts:sig" — split from right to handle any colons in future
        parts = token.rsplit(":", 2)
        if len(parts) != 3:
            return None
        user_id_s, ts_s, sig = parts
        payload = f"{user_id_s}:{ts_s}"
        expected = _hmac.new(
            _SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return None
        if time.time() - int(ts_s) > _SESSION_MAX_AGE:
            return None
        return int(user_id_s)
    except Exception:
        return None


def _inject_js(script: str) -> None:
    """Inject JavaScript via components.v1.html which has allow-same-origin.

    st.html() sandboxes content without allow-same-origin, so document.cookie
    writes go to a null origin and are never sent to the server.
    st.components.v1.html() uses a different iframe policy that allows
    same-origin cookie access.
    """
    _components.html(f"<script>{script}</script>", height=0)


def set_session_cookie() -> None:
    """Write signed session cookie to browser via JavaScript injection."""
    user_id = get_current_user_id()
    if not user_id:
        return
    token = _sign_token(user_id)
    _inject_js(
        f"document.cookie='{_SESSION_COOKIE}={token}; path=/; "
        f"max-age={_SESSION_MAX_AGE}; SameSite=Strict';"
    )


def clear_session_cookie() -> None:
    """Delete session cookie from browser via JavaScript injection."""
    _inject_js(
        f"document.cookie='{_SESSION_COOKIE}=; path=/; max-age=0; SameSite=Strict';"
    )


def try_restore_from_cookie() -> None:
    """On fresh page load, try to restore session from cookie.

    Must be called at the very top of app.py, before require_auth().
    """
    import sys
    if require_auth():
        return  # Already authenticated via session_state
    try:
        token = st.context.cookies.get(_SESSION_COOKIE)
    except Exception as e:
        print(f"[AUTH DEBUG] try_restore_from_cookie exception: {e}", file=sys.stderr)
        return
    if not token:
        print("[AUTH DEBUG] try_restore_from_cookie: no token in cookie", file=sys.stderr)
        return
    user_id = _verify_token(token)
    print(f"[AUTH DEBUG] _verify_token result: {user_id}", file=sys.stderr)
    if user_id:
        load_user_session(user_id)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return bcrypt hash of a plain-text password."""
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt is not installed. Run: pip install bcrypt")
    hashed = _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored bcrypt hash."""
    if not _BCRYPT_AVAILABLE:
        return False
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_current_user_id() -> Optional[int]:
    """Return current user's id from session_state, or None."""
    return st.session_state.get("user_id")


def get_current_user_settings() -> Dict[str, Any]:
    """Return current user's settings dict from session_state."""
    return st.session_state.get("user_settings", {})


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value for current user."""
    return get_current_user_settings().get(key, default)


def load_user_session(user_id: int) -> None:
    """Load user data into session_state after successful login."""
    st.session_state["user_id"] = user_id
    st.session_state["user_settings"] = get_user_settings(user_id)


def require_auth() -> bool:
    """Return True if user is authenticated."""
    return bool(st.session_state.get("user_id"))


def logout() -> None:
    """Clear authentication state from session."""
    for key in ["user_id", "user_settings"]:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Login / registration UI
# ---------------------------------------------------------------------------

def render_login_form() -> bool:
    """
    Render login / first-user-registration form.
    Returns True if the user just logged in (caller should trigger st.rerun()).
    """
    is_first_user = count_users() == 0

    if is_first_user:
        st.info("No users yet. Create the first account.")
        return _render_register_form(is_first=True)

    tab_login, tab_register = st.tabs(["Sign in", "Register"])

    with tab_login:
        logged_in = _render_login_tab()

    with tab_register:
        registered = _render_register_form(is_first=False)

    return logged_in or registered


def _render_login_tab() -> bool:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if not submitted:
        return False

    if not username or not password:
        st.error("Please enter username and password.")
        return False

    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        st.error("Invalid username or password.")
        return False

    load_user_session(user["id"])
    return True


def _render_register_form(is_first: bool) -> bool:
    label = "Create first account" if is_first else "Register"
    with st.form(f"register_form_{'first' if is_first else 'new'}"):
        username = st.text_input("Username")
        email = st.text_input("Email (optional)")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button(label, type="primary")

    if not submitted:
        return False

    username = (username or "").strip()
    email = (email or "").strip() or None
    if not username:
        st.error("Username is required.")
        return False
    if not password:
        st.error("Password is required.")
        return False
    if password != confirm:
        st.error("Passwords do not match.")
        return False
    if get_user_by_username(username):
        st.error("Username already taken.")
        return False

    hashed = hash_password(password)
    user_id = create_user(username, hashed, email=email)
    load_user_session(user_id)
    return True
