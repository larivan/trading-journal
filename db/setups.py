# db/setups.py — Setup CRUD operations
import sqlite3
from typing import Any, Dict, List, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


SETUP_WRITABLE_FIELDS = [
    "name",
    "description",
]

SETUP_SELECT_COLUMNS = [
    "id",
    "user_id",
    "name",
    "description",
]

SETUP_ORDER_COLUMNS = {
    "id": "id",
    "name": "name",
}


def _normalize_setup_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in SETUP_WRITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue
        if key == "name":
            payload[key] = str(value).strip()
            continue
        if key == "description":
            payload[key] = str(value).strip() or None
            continue
        payload[key] = value
    return payload


def create_setup(
    user_id: int,
    name: str,
    description: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    payload = _normalize_setup_payload(
        {"name": name, "description": description}
    )
    name_value = (payload.get("name") or "").strip()
    if not name_value:
        raise ValueError("name is required for setup.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO setups (user_id, name, description) VALUES (?, ?, ?)",
            (user_id, name_value, payload.get("description")),
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def list_setups(
    user_id: int,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(SETUP_SELECT_COLUMNS)
    q = f"SELECT {select_clause} FROM setups WHERE user_id=?"
    params: List[Any] = [user_id]

    for key, value in filters.items():
        if value in (None, ""):
            continue
        if key == "query":
            pattern = f"%{value}%"
            q += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([pattern, pattern])

    if order_by:
        if order_by not in SETUP_ORDER_COLUMNS:
            raise ValueError(
                f"order_by must be one of: {sorted(SETUP_ORDER_COLUMNS)}"
            )
        q += (
            f" ORDER BY {SETUP_ORDER_COLUMNS[order_by]} "
            f"{'ASC' if ascending else 'DESC'}"
        )
    else:
        q += " ORDER BY name ASC, id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(q, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_setup(setup_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {', '.join(SETUP_SELECT_COLUMNS)} FROM setups WHERE id=? AND user_id=?",
            (setup_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_setup(
    setup_id: int,
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    payload = _normalize_setup_payload(data or {})
    if not payload:
        return

    name_value = payload.get("name")
    if name_value is not None and not name_value.strip():
        raise ValueError("name is required for setup.")

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE setups SET {assignments} WHERE id=? AND user_id=?",
            values + [setup_id, user_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Setup #{setup_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_setup(
    setup_id: int,
    user_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if setup_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM setups WHERE id=? AND user_id=?", (setup_id, user_id))
        if cur.rowcount == 0:
            raise ValueError(f"Setup #{setup_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()
