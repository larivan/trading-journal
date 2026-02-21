# db/accounts.py — Account CRUD operations
import sqlite3
from typing import Any, Dict, List, Optional

from db._normalize import coerce_float
from db.connection import get_conn, _managed_conn, _now_iso_utc, _rows_to_dicts


ACCOUNT_WRITABLE_FIELDS = [
    "name",
    "broker",
    "currency",
    "starting_balance",
    "is_prop",
]


def _normalize_account_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize account data, filtering by ACCOUNT_WRITABLE_FIELDS whitelist."""
    payload: Dict[str, Any] = {}
    for key in ACCOUNT_WRITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue

        if key == "name":
            name = str(value).strip()
            if not name:
                raise ValueError("Account name cannot be empty.")
            payload[key] = name
            continue

        if key == "starting_balance":
            payload[key] = coerce_float(key, value)
            continue

        if key == "is_prop":
            try:
                payload[key] = int(bool(value))
            except (TypeError, ValueError):
                payload[key] = 0
            continue

        # String fields: broker, currency
        payload[key] = value

    return payload


def create_account(
    name: str,
    broker: Optional[str] = None,
    currency: str = "USD",
    starting_balance: Optional[float] = None,
    is_prop: int = 0,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO accounts (name, broker, currency, starting_balance, is_prop, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, broker, currency, starting_balance, is_prop, _now_iso_utc()),
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def list_accounts(include_archived: bool = False) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        query = "SELECT * FROM accounts"
        if not include_archived:
            query += " WHERE archived IS NULL OR archived=0"
        query += " ORDER BY id ASC"
        rows = conn.execute(query).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_account(account_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_account(
    account_id: int,
    data: Dict[str, Any],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if not data:
        return

    payload = _normalize_account_payload(data)
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE accounts SET {assignments} WHERE id=?",
            values + [account_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Account #{account_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def set_account_archived(
    account_id: int,
    archived: bool = True,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE accounts SET archived=? WHERE id=?",
            (1 if archived else 0, account_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Account #{account_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_account(
    account_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if account_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Account #{account_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()
