# db/analysis.py — Analysis CRUD operations
import sqlite3
from typing import Any, Dict, List, Optional

from db._normalize import normalize_date
from db.connection import get_conn, _managed_conn, _rows_to_dicts


ANALYSIS_COLUMNS = [
    "id",
    "user_id",
    "date_local",
    "asset",
    "daily_bias",
    "fact_bias",
    "day_result",
]

ANALYSIS_WRITABLE_FIELDS = [
    "date_local",
    "asset",
    "daily_bias",
    "fact_bias",
    "day_result",
]

ANALYSIS_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "asset": "asset",
    "daily_bias": "daily_bias",
    "fact_bias": "fact_bias",
    "day_result": "day_result",
}


def _normalize_analysis_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in ANALYSIS_WRITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue
        if key == "date_local":
            payload[key] = normalize_date(value)
            continue
        payload[key] = value
    return payload


# =====================================================================
# Analysis (daily overview)
# =====================================================================


def add_analysis(
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    payload = _normalize_analysis_payload(data)
    if "date_local" not in payload:
        raise ValueError("date_local is required for analysis.")

    payload["user_id"] = user_id
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO analysis ({columns}) VALUES ({placeholders})",
            values,
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def list_analysis(
    user_id: int,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = False,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(ANALYSIS_COLUMNS)
    q = f"SELECT {select_clause} FROM analysis WHERE user_id=?"
    params: List[Any] = [user_id]

    mapping = {
        "asset": "asset",
        "daily_bias": "daily_bias",
        "fact_bias": "fact_bias",
        "day_result": "day_result",
        "date_from": "date_local >= ?",
        "date_to": "date_local <= ?",
    }
    for key, value in filters.items():
        if value is None:
            continue
        if key in ("date_from", "date_to"):
            q += f" AND {mapping[key]}"
            params.append(value)
        elif key in mapping:
            q += f" AND {mapping[key]} = ?"
            params.append(value)

    if order_by:
        if order_by not in ANALYSIS_ORDER_COLUMNS:
            raise ValueError(
                f"order_by must be one of: {sorted(ANALYSIS_ORDER_COLUMNS)}"
            )
        q += (
            f" ORDER BY {ANALYSIS_ORDER_COLUMNS[order_by]} "
            f"{'ASC' if ascending else 'DESC'}"
        )
    else:
        q += " ORDER BY date_local DESC, id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(q, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_analysis(analysis_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {', '.join(ANALYSIS_COLUMNS)} FROM analysis WHERE id=? AND user_id=?",
            (analysis_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_analysis(
    analysis_id: int,
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    payload = _normalize_analysis_payload(data)
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE analysis SET {assignments} WHERE id=? AND user_id=?",
            values + [analysis_id, user_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Analysis #{analysis_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_analysis(
    analysis_id: int,
    user_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis WHERE id=? AND user_id=?", (analysis_id, user_id))
        if cur.rowcount == 0:
            raise ValueError(f"Analysis #{analysis_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def attach_image_to_analysis(
    analysis_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Прикрепляет изображение напрямую к анализу."""
    conn, own = _managed_conn(conn)
    try:
        conn.execute(
            "UPDATE images SET analysis_id=? WHERE id=?",
            (analysis_id, image_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()
