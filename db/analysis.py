# db/analysis.py — Analysis CRUD operations
import json
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
]

ANALYSIS_WRITABLE_FIELDS = [
    "date_local",
    "asset",
    "daily_bias",
    "fact_bias",
]

ANALYSIS_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "asset": "asset",
    "daily_bias": "daily_bias",
    "fact_bias": "fact_bias",
}

_DAY_RESULT_SQL = """\
    CASE
        WHEN COUNT(CASE WHEN t.net_pnl IS NOT NULL AND (t.is_missed IS NULL OR t.is_missed = 0) THEN 1 END) = 0 THEN NULL
        WHEN SUM(CASE WHEN t.net_pnl IS NOT NULL AND (t.is_missed IS NULL OR t.is_missed = 0) THEN t.net_pnl ELSE 0 END) > 0 THEN 'Profit'
        WHEN SUM(CASE WHEN t.net_pnl IS NOT NULL AND (t.is_missed IS NULL OR t.is_missed = 0) THEN t.net_pnl ELSE 0 END) < 0 THEN 'Loss'
        ELSE 'Breakeven'
    END AS day_result\
"""


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
        if key == "asset":
            if isinstance(value, list):
                payload[key] = json.dumps(value)
            else:
                payload[key] = json.dumps([value]) if value else json.dumps([])
            continue
        payload[key] = value
    return payload


def _deserialize_analysis(row: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize asset JSON string to list."""
    raw = row.get("asset")
    if isinstance(raw, list):
        return row
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            row["asset"] = parsed if isinstance(parsed, list) else ([parsed] if parsed is not None else [])
        except (json.JSONDecodeError, TypeError):
            row["asset"] = [raw] if raw else []
    else:
        row["asset"] = []
    return row


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
    if "asset" not in payload or json.loads(payload["asset"]) == []:
        raise ValueError("asset is required for analysis.")

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
    a_cols = ", ".join(f"a.{c}" for c in ANALYSIS_COLUMNS)
    q = (
        f"SELECT {a_cols}, {_DAY_RESULT_SQL} "
        f"FROM analysis a LEFT JOIN trades t ON t.analysis_id = a.id "
        f"WHERE a.user_id=?"
    )
    params: List[Any] = [user_id]

    mapping = {
        "daily_bias": "a.daily_bias",
        "fact_bias": "a.fact_bias",
        "date_from": "a.date_local >= ?",
        "date_to": "a.date_local <= ?",
    }
    for key, value in filters.items():
        if value is None:
            continue
        if key in ("date_from", "date_to"):
            q += f" AND {mapping[key]}"
            params.append(value)
        elif key == "asset":
            q += " AND EXISTS (SELECT 1 FROM json_each(a.asset) WHERE value = ?)"
            params.append(value)
        elif key in mapping:
            q += f" AND {mapping[key]} = ?"
            params.append(value)

    q += " GROUP BY a.id"

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
        q += " ORDER BY a.date_local DESC, a.id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(q, params).fetchall()
        return [_deserialize_analysis(r) for r in _rows_to_dicts(rows)]
    finally:
        conn.close()


def get_analysis(analysis_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    a_cols = ", ".join(f"a.{c}" for c in ANALYSIS_COLUMNS)
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {a_cols}, {_DAY_RESULT_SQL} "
            f"FROM analysis a LEFT JOIN trades t ON t.analysis_id = a.id "
            f"WHERE a.id=? AND a.user_id=? GROUP BY a.id",
            (analysis_id, user_id),
        ).fetchone()
        return _deserialize_analysis(dict(row)) if row else None
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

