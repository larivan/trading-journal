# utils/auth.py — Authentication helpers (bcrypt + session_state)
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

try:
    import bcrypt as _bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

from db.users import get_user_by_username, get_user_settings, create_user, count_users


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


def render_login_form() -> bool:
    """
    Render login / first-user-registration form.
    Returns True if the user just logged in (trigger st.rerun()).
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
