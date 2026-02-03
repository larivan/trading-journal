# db/trades.py — Trade CRUD operations
import sqlite3
from typing import Any, Dict, List, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


TRADE_ORDER_COLUMNS = {
    "id",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "state",
    "is_missed",
    "session",
    "net_pnl",
    "risk_reward",
    "reward_percent",
}

TRADE_COLUMNS = [
    "id",
    "local_tz",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "risk_pct",
    "session",
    "state",
    "is_missed",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "estimation",
    "emotional_problems",
    "hot_thoughts",
    "cold_thoughts",
]

WRITABLE_TRADE_FIELDS = [
    "local_tz",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "risk_pct",
    "session",
    "state",
    "is_missed",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "estimation",
    "emotional_problems",
    "hot_thoughts",
    "cold_thoughts",
]


def get_trade_by_id(trade_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM trades WHERE id=?",
                           (trade_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_trade(
    data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> int:
    if not data:
        raise ValueError("Нет данных для создания сделки.")

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    values = list(data.values())

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
    trade_id: int, data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if not data:
        return

    assignments = ", ".join(f"{col}=?" for col in data.keys())
    values = list(data.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE trades SET {assignments} WHERE id=?",
            values + [trade_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Сделка #{trade_id} не найдена.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_trade(trade_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    if trade_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades WHERE id=?", (trade_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Сделка #{trade_id} не найдена.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_trades(
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(TRADE_COLUMNS)
    q = f"SELECT {select_clause} FROM trades WHERE 1=1"
    p: List[Any] = []

    mapping = {
        "account_id": "account_id",
        "asset": "asset",
        "setup_id": "setup_id",
        "analysis_id": "analysis_id",
        "state": "state",
        "is_missed": "is_missed",
        "session": "session",
        "estimation": "estimation",
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
        return _rows_to_dicts(rows)
    finally:
        conn.close()
