# db/notes.py — Notes CRUD operations and relations
import sqlite3
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


NOTE_WRITABLE_FIELDS = [
    "body",
    "date_local",
    "time_local",
]

NOTE_SELECT_COLUMNS = [
    "id",
    "body",
    "date_local",
    "time_local",
]

NOTE_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "time_local": "time_local",
}


def _normalize_note_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in NOTE_WRITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue
        if key == "body":
            payload[key] = str(value).strip()
            continue
        if key == "date_local" and isinstance(value, date):
            payload[key] = value.isoformat()
            continue
        if key == "time_local":
            if isinstance(value, time):
                payload[key] = value.strftime("%H:%M:%S")
            elif isinstance(value, datetime):
                payload[key] = value.strftime("%H:%M:%S")
            else:
                payload[key] = str(value)
            continue
        payload[key] = value
    return payload


def create_note(
    data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> int:
    payload = _normalize_note_payload(data or {})
    body_value = (payload.get("body") or "").strip()
    if not body_value:
        raise ValueError("body is required for note.")

    payload["body"] = body_value
    payload.setdefault("date_local", date.today().isoformat())
    payload.setdefault("time_local", datetime.now().strftime("%H:%M:%S"))

    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO notes ({columns}) VALUES ({placeholders})",
            values,
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def list_notes(
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = False,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(NOTE_SELECT_COLUMNS)
    q = f"SELECT {select_clause} FROM notes WHERE 1=1"
    params: List[Any] = []

    mapping = {
        "date_from": "date_local >= ?",
        "date_to": "date_local <= ?",
    }
    for key, value in filters.items():
        if value in (None, ""):
            continue
        if key in ("date_from", "date_to"):
            q += f" AND {mapping[key]}"
            params.append(value)
        elif key == "query":
            pattern = f"%{value}%"
            q += " AND (body LIKE ?)"
            params.append(pattern)

    if order_by:
        if order_by not in NOTE_ORDER_COLUMNS:
            raise ValueError(
                f"order_by must be one of: {sorted(NOTE_ORDER_COLUMNS)}")
        q += (
            f" ORDER BY {NOTE_ORDER_COLUMNS[order_by]} "
            f"{'ASC' if ascending else 'DESC'}"
        )
    else:
        q += " ORDER BY date_local DESC, time_local DESC, id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(q, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {', '.join(NOTE_SELECT_COLUMNS)} FROM notes WHERE id=?",
            (note_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_note(
    note_id: int, data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> None:
    payload = _normalize_note_payload(data or {})
    if "body" in payload:
        body_value = (payload["body"] or "").strip()
        if not body_value:
            raise ValueError("body is required for note.")
        payload["body"] = body_value
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE notes SET {assignments} WHERE id=?",
            values + [note_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Note #{note_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_note(note_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    if note_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM charts WHERE note_id=?", (note_id,))
        cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Note #{note_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


# =====================================================================
# Note relations with trades
# =====================================================================


def attach_note_to_trade(
    trade_id: int, note_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if trade_id is None or note_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO trade_notes (trade_id, note_id) VALUES (?, ?)",
            (trade_id, note_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_note_from_trade(
    trade_id: int, note_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if trade_id is None or note_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM trade_notes WHERE trade_id=? AND note_id=?",
            (trade_id, note_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_trade_notes(trade_id: int) -> List[Dict[str, Any]]:
    if trade_id is None:
        return []
    conn = get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT {', '.join(NOTE_SELECT_COLUMNS)}
            FROM notes n
            JOIN trade_notes tn ON tn.note_id = n.id
            WHERE tn.trade_id=?
            ORDER BY n.date_local DESC, n.time_local DESC, n.id DESC
            """,
            (trade_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def count_notes_by_trade() -> Dict[int, int]:
    """Count how many trades each note is linked to (single query, no N+1)."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT note_id, COUNT(*) as cnt FROM trade_notes GROUP BY note_id"
        ).fetchall()
        return {row["note_id"]: row["cnt"] for row in rows}
    finally:
        conn.close()


# =====================================================================
# Note relations with analysis stages
# =====================================================================


def attach_note_to_analysis_stage(
    stage_id: int, note_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if stage_id is None or note_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO analysis_notes (analysis_stage_id, note_id) VALUES (?, ?)",
            (stage_id, note_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_note_from_analysis_stage(
    stage_id: int, note_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    if stage_id is None or note_id is None:
        return
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM analysis_notes WHERE analysis_stage_id=? AND note_id=?",
            (stage_id, note_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_analysis_stage_notes(stage_id: int) -> List[Dict[str, Any]]:
    if stage_id is None:
        return []
    conn = get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT {', '.join(NOTE_SELECT_COLUMNS)}
            FROM notes n
            JOIN analysis_notes an ON an.note_id = n.id
            WHERE an.analysis_stage_id=?
            ORDER BY n.date_local DESC, n.time_local DESC, n.id DESC
            """,
            (stage_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()
