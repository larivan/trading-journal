# db/users.py — User and user_settings CRUD operations
import json
import sqlite3
from typing import Any, Dict, List, Optional

from db.connection import get_conn, _managed_conn, _now_iso_utc, _rows_to_dicts


WRITABLE_SETTING_FIELDS = [
    "assets",
    "be_threshold",
    "risk_min",
    "risk_max",
    "local_tz",
    "currency",
    "theme",
    "language",
]

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "assets": ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"],
    "be_threshold": 0.05,
    "risk_min": 0.5,
    "risk_max": 2.0,
    "local_tz": "Europe/Moscow",
    "currency": "USD",
    "theme": "light",
    "language": "en",
}


def create_user(
    email: str,
    username: str = "",
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Create user and default settings. Returns new user id."""
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, username, created_at) VALUES (?, ?, ?)",
            (email, username, _now_iso_utc()),
        )
        user_id = cur.lastrowid
        cur.execute(
            "INSERT INTO user_settings (user_id, local_tz) VALUES (?, ?)",
            (user_id, _DEFAULT_SETTINGS["local_tz"]),
        )
        if own:
            conn.commit()
        return user_id
    finally:
        if own:
            conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Return user settings with defaults. assets is parsed from JSON."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return dict(_DEFAULT_SETTINGS)
        result = dict(_DEFAULT_SETTINGS)
        result.update({k: v for k, v in dict(row).items() if v is not None})
        # Parse assets JSON
        if isinstance(result.get("assets"), str):
            try:
                result["assets"] = json.loads(result["assets"])
            except (json.JSONDecodeError, TypeError):
                result["assets"] = _DEFAULT_SETTINGS["assets"]
        return result
    finally:
        conn.close()


def update_user_settings(
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Update user settings. Only WRITABLE_SETTING_FIELDS are accepted."""
    payload: Dict[str, Any] = {}
    for key in WRITABLE_SETTING_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if key == "assets":
            if isinstance(value, list):
                payload[key] = json.dumps(value)
            else:
                payload[key] = value
        elif key == "be_threshold":
            payload[key] = float(value) if value is not None else 0.05
        elif key in ("risk_min", "risk_max"):
            payload[key] = float(value) if value is not None else None
        else:
            payload[key] = value

    if not payload:
        return

    conn, own = _managed_conn(conn)
    try:
        assignments = ", ".join(f"{col}=?" for col in payload.keys())
        values = list(payload.values())
        conn.execute(
            f"UPDATE user_settings SET {assignments} WHERE user_id=?",
            values + [user_id],
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_users() -> List[Dict[str, Any]]:
    """Return all active users (for admin panel)."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, username, email, created_at, is_active FROM users ORDER BY id ASC"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()
