# utils/auth.py — Authentication helpers (OAuth via st.login + session_state)
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from db.users import get_user_by_email, get_user_settings, create_user


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
    """Return True if user is authenticated (user_id is in session_state)."""
    return bool(st.session_state.get("user_id"))


def logout() -> None:
    """Clear authentication state from session."""
    for key in ["user_id", "user_settings"]:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

def ensure_user_from_oauth() -> None:
    """При первом логине через OAuth создать запись в БД, при повторных — найти."""
    if require_auth():
        return
    email = st.user.email
    name = getattr(st.user, "name", "") or ""
    user = get_user_by_email(email)
    if user is None:
        user_id = create_user(email=email, username=name)
    else:
        user_id = user["id"]
    load_user_session(user_id)
