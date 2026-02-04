# db/charts.py — Charts CRUD and attachment operations
import sqlite3
from typing import Any, Dict, List, Literal, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


# Entity types for chart attachments
EntityType = Literal["trade", "analysis_stage", "setup", "note"]

# Mapping from entity type to column name
_ENTITY_COLUMNS: Dict[EntityType, str] = {
    "trade": "trade_id",
    "analysis_stage": "analysis_stage_id",
    "setup": "setup_id",
    "note": "note_id",
}

# Error messages for each entity type
_ENTITY_LABELS: Dict[EntityType, str] = {
    "trade": "сделке",
    "analysis_stage": "этапу анализа",
    "setup": "сетапу",
    "note": "заметке",
}


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
# Universal chart attachment functions
# =====================================================================


def attach_chart(
    entity_type: EntityType,
    entity_id: int,
    chart_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Attach a chart to an entity.
    
    Args:
        entity_type: One of 'trade', 'analysis_stage', 'setup', 'note'
        entity_id: ID of the entity to attach to
        chart_id: ID of the chart to attach
        conn: Optional database connection
    
    Raises:
        ValueError: If chart not found or already attached to another entity
    """
    if entity_type not in _ENTITY_COLUMNS:
        raise ValueError(f"Unknown entity type: {entity_type}")
    
    target_column = _ENTITY_COLUMNS[entity_type]
    other_columns = [col for et, col in _ENTITY_COLUMNS.items() if et != entity_type]
    
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        
        # Check if attached to another entity type
        for col in other_columns:
            if chart_row[col]:
                raise ValueError("Чарт уже привязан к другой сущности.")
        
        # Check if attached to different entity of same type
        if chart_row[target_column] not in (None, entity_id):
            label = _ENTITY_LABELS[entity_type]
            raise ValueError(f"Чарт уже привязан к другой {label}.")
        
        # Build UPDATE: set target column, clear others
        set_parts = [f"{target_column}=?"]
        set_parts.extend(f"{col}=NULL" for col in other_columns)
        
        cur.execute(
            f"UPDATE charts SET {', '.join(set_parts)} WHERE id=?",
            (entity_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart(
    entity_type: EntityType,
    entity_id: int,
    chart_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Detach a chart from an entity.
    
    Args:
        entity_type: One of 'trade', 'analysis_stage', 'setup', 'note'
        entity_id: ID of the entity to detach from
        chart_id: ID of the chart to detach
        conn: Optional database connection
    """
    if entity_type not in _ENTITY_COLUMNS:
        raise ValueError(f"Unknown entity type: {entity_type}")
    
    column = _ENTITY_COLUMNS[entity_type]
    
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE charts SET {column}=NULL WHERE {column}=? AND id=?",
            (entity_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


# =====================================================================
# Backwards-compatible wrapper functions
# =====================================================================


def attach_chart_to_trade(
    trade_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach chart to trade. Wrapper for attach_chart()."""
    attach_chart("trade", trade_id, chart_id, conn=conn)


def detach_chart_from_trade(
    trade_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach chart from trade. Wrapper for detach_chart()."""
    detach_chart("trade", trade_id, chart_id, conn=conn)


def attach_chart_to_analysis_stage(
    stage_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach chart to analysis stage. Wrapper for attach_chart()."""
    attach_chart("analysis_stage", stage_id, chart_id, conn=conn)


def detach_chart_from_analysis_stage(
    stage_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach chart from analysis stage. Wrapper for detach_chart()."""
    detach_chart("analysis_stage", stage_id, chart_id, conn=conn)


def attach_chart_to_setup(
    setup_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach chart to setup. Wrapper for attach_chart()."""
    attach_chart("setup", setup_id, chart_id, conn=conn)


def detach_chart_from_setup(
    setup_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach chart from setup. Wrapper for detach_chart()."""
    detach_chart("setup", setup_id, chart_id, conn=conn)


def attach_chart_to_note(
    note_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach chart to note. Wrapper for attach_chart()."""
    attach_chart("note", note_id, chart_id, conn=conn)


def detach_chart_from_note(
    note_id: int, chart_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach chart from note. Wrapper for detach_chart()."""
    detach_chart("note", note_id, chart_id, conn=conn)
