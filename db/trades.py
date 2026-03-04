# db/trades.py — Trade CRUD operations
import json
import sqlite3
from typing import Any, Dict, List, Optional

from config import TRADE_SESSION_VALUES
from db._normalize import coerce_float, coerce_int, normalize_date, normalize_time
from db.connection import get_conn, _managed_conn, _rows_to_dicts


TRADE_ORDER_COLUMNS = {
    "id",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "trade_type",
    "is_missed",
    "session",
    "net_pnl",
    "risk_reward",
    "reward_percent",
}

TRADE_COLUMNS = [
    "id",
    "user_id",
    "local_tz",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "trade_type",
    "risk_pct",
    "session",
    "is_missed",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "is_correct",
    "mistake_types",
]

WRITABLE_TRADE_FIELDS = [
    "local_tz",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "trade_type",
    "risk_pct",
    "session",
    "is_missed",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "is_correct",
    "mistake_types",
]

_INT_FIELDS = {"account_id", "setup_id", "analysis_id", "is_missed", "is_correct"}
_FLOAT_FIELDS = {"risk_pct", "net_pnl", "risk_reward", "reward_percent"}


def _compute_status(t: dict) -> str:
    if t.get("is_correct") is not None:
        return "Reviewed"
    if t.get("net_pnl") is not None or t.get("is_missed"):
        return "Outcome"
    return "Open"


def _normalize_trade_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize trade data, filtering by WRITABLE_TRADE_FIELDS whitelist."""
    payload: Dict[str, Any] = {}
    for key in WRITABLE_TRADE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue

        if key == "date_local":
            payload[key] = normalize_date(value)
            continue

        if key == "time_local":
            payload[key] = normalize_time(value)
            continue

        if key == "session":
            if value not in TRADE_SESSION_VALUES:
                raise ValueError(
                    f"session must be one of: {', '.join(TRADE_SESSION_VALUES)}"
                )
            payload[key] = value
            continue

        if key == "mistake_types":
            if isinstance(value, list):
                payload[key] = json.dumps(value)
            else:
                payload[key] = value
            continue

        if key in _INT_FIELDS:
            payload[key] = coerce_int(key, value)
            continue

        if key in _FLOAT_FIELDS:
            payload[key] = coerce_float(key, value)
            continue

        payload[key] = value

    return payload


def get_trade_by_id(trade_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM trades WHERE id=? AND user_id=?",
            (trade_id, user_id),
        ).fetchone()
        if not row:
            return None
        t = dict(row)
        t["status"] = _compute_status(t)
        return t
    finally:
        conn.close()


def create_trade(
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    if not data:
        raise ValueError("No data to create trade.")

    payload = _normalize_trade_payload(data)
    if not payload:
        raise ValueError("No valid fields to create trade.")

    payload["user_id"] = user_id
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO trades ({columns}) VALUES ({placeholders})",
            values,
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def update_trade(
    trade_id: int,
    user_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if not data:
        return

    payload = _normalize_trade_payload(data)
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE trades SET {assignments} WHERE id=? AND user_id=?",
            values + [trade_id, user_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Trade #{trade_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_trade(
    trade_id: int,
    user_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if trade_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades WHERE id=? AND user_id=?", (trade_id, user_id))
        if cur.rowcount == 0:
            raise ValueError(f"Trade #{trade_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_trades(
    user_id: int,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(TRADE_COLUMNS)
    q = f"SELECT {select_clause} FROM trades WHERE user_id=?"
    p: List[Any] = [user_id]

    mapping = {
        "account_id": "account_id",
        "asset": "asset",
        "trade_type": "trade_type",
        "setup_id": "setup_id",
        "analysis_id": "analysis_id",
        "is_missed": "is_missed",
        "session": "session",
        "is_correct": "is_correct",
        "date_from": "date_local >= ?",
        "date_to": "date_local <= ?",
    }
    for k, v in filters.items():
        if v is None:
            continue
        if k in ("date_from", "date_to"):
            q += f" AND {mapping[k]}"
            p.append(v)
        elif k in mapping:
            q += f" AND {mapping[k]} = ?"
            p.append(v)
        elif k == "result":
            from config import BE_THRESHOLD
            if v == "Win":
                q += " AND risk_reward > ? AND is_missed = 0"
                p.append(BE_THRESHOLD)
            elif v == "Loss":
                q += " AND risk_reward < ? AND is_missed = 0"
                p.append(-BE_THRESHOLD)
            elif v == "BE":
                q += " AND risk_reward BETWEEN ? AND ? AND is_missed = 0"
                p.extend([-BE_THRESHOLD, BE_THRESHOLD])
            elif v == "Miss":
                q += " AND is_missed = 1"

    if order_by:
        if order_by not in TRADE_ORDER_COLUMNS:
            raise ValueError(
                f"order_by must be one of: {sorted(TRADE_ORDER_COLUMNS)}")
        q += f" ORDER BY {order_by} {'ASC' if ascending else 'DESC'}"
    else:
        q += " ORDER BY date_local DESC, id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(q, p).fetchall()
        result = _rows_to_dicts(rows)
        for t in result:
            t["status"] = _compute_status(t)
        return result
    finally:
        conn.close()
