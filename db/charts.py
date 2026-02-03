# db/charts.py — Charts CRUD and attachment operations
import sqlite3
from typing import Any, Dict, List, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


def add_chart(
    chart_url: str,
    caption: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO charts (chart_url, caption) VALUES (?, ?)",
            (chart_url, caption),
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def get_chart(chart_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM charts WHERE id=?",
                           (chart_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_chart(
    chart_id: int,
    chart_url: str,
    caption: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE charts
            SET chart_url=?, caption=?
            WHERE id=?
            """,
            (chart_url, caption, chart_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_chart(chart_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM charts WHERE id=?", (chart_id,))
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_charts(
    *,
    trade_id: Optional[int] = None,
    analysis_stage_id: Optional[int] = None,
    setup_id: Optional[int] = None,
    note_id: Optional[int] = None,
    unattached: bool = False,
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []

    if trade_id is not None:
        conditions.append("trade_id=?")
        params.append(trade_id)
    if analysis_stage_id is not None:
        conditions.append("analysis_stage_id=?")
        params.append(analysis_stage_id)
    if setup_id is not None:
        conditions.append("setup_id=?")
        params.append(setup_id)
    if note_id is not None:
        conditions.append("note_id=?")
        params.append(note_id)
    if unattached:
        conditions.append("trade_id IS NULL")
        conditions.append("analysis_stage_id IS NULL")
        conditions.append("setup_id IS NULL")
        conditions.append("note_id IS NULL")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM charts {where_clause} ORDER BY id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# =====================================================================
# Chart attachments to entities
# =====================================================================


def attach_chart_to_trade(
    trade_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["analysis_stage_id"] or chart_row["setup_id"] or chart_row["note_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["trade_id"] not in (None, trade_id):
            raise ValueError("Чарт уже привязан к другой сделке.")
        cur.execute(
            "UPDATE charts SET trade_id=?, analysis_stage_id=NULL, setup_id=NULL, note_id=NULL WHERE id=?",
            (trade_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_trade(
    trade_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE charts SET trade_id=NULL WHERE trade_id=? AND id=?",
            (trade_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def attach_chart_to_analysis_stage(
    stage_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["trade_id"] or chart_row["setup_id"] or chart_row["note_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["analysis_stage_id"] not in (None, stage_id):
            raise ValueError("Чарт уже привязан к другому этапу анализа.")
        cur.execute(
            "UPDATE charts SET analysis_stage_id=?, trade_id=NULL, setup_id=NULL, note_id=NULL WHERE id=?",
            (stage_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_analysis_stage(
    stage_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE charts SET analysis_stage_id=NULL WHERE analysis_stage_id=? AND id=?",
            (stage_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def attach_chart_to_setup(
    setup_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["trade_id"] or chart_row["analysis_stage_id"] or chart_row["note_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["setup_id"] not in (None, setup_id):
            raise ValueError("Чарт уже привязан к другому сетапу.")
        cur.execute(
            "UPDATE charts SET setup_id=?, trade_id=NULL, analysis_stage_id=NULL, note_id=NULL WHERE id=?",
            (setup_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_setup(
    setup_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE charts SET setup_id=NULL WHERE setup_id=? AND id=?",
            (setup_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def attach_chart_to_note(
    note_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["trade_id"] or chart_row["analysis_stage_id"] or chart_row["setup_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["note_id"] not in (None, note_id):
            raise ValueError("Чарт уже привязан к другой заметке.")
        cur.execute(
            "UPDATE charts SET note_id=?, trade_id=NULL, analysis_stage_id=NULL, setup_id=NULL WHERE id=?",
            (note_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_note(
    note_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE charts SET note_id=NULL WHERE note_id=? AND id=?",
            (note_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()
