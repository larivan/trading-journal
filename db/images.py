# db/images.py — Images CRUD and attachment operations
import sqlite3
from typing import Any, Dict, List, Literal, Optional

from db.connection import get_conn, _managed_conn, _rows_to_dicts


# Entity types for image attachments
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
    "trade": "trade",
    "analysis_stage": "analysis stage",
    "setup": "setup",
    "note": "note",
}


def add_image(
    image_url: str,
    caption: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    if not image_url:
        raise ValueError("image_url is required.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO images (image_url, caption) VALUES (?, ?)",
            (image_url, caption),
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def get_image(image_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM images WHERE id=?",
                           (image_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_image(
    image_id: int,
    image_url: str,
    caption: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    if not image_url:
        raise ValueError("image_url is required.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE images
            SET image_url=?, caption=?
            WHERE id=?
            """,
            (image_url, caption, image_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Image #{image_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_image(image_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE id=?", (image_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Image #{image_id} not found.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_images(
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
    query = f"SELECT * FROM images {where_clause} ORDER BY id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# =====================================================================
# Universal image attachment functions
# =====================================================================


def attach_image(
    entity_type: EntityType,
    entity_id: int,
    image_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Attach an image to an entity.

    Args:
        entity_type: One of 'trade', 'analysis_stage', 'setup', 'note'
        entity_id: ID of the entity to attach to
        image_id: ID of the image to attach
        conn: Optional database connection

    Raises:
        ValueError: If image not found or already attached to another entity
    """
    if entity_type not in _ENTITY_COLUMNS:
        raise ValueError(f"Unknown entity type: {entity_type}")

    target_column = _ENTITY_COLUMNS[entity_type]
    other_columns = [col for et, col in _ENTITY_COLUMNS.items() if et != entity_type]

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        image_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id, note_id FROM images WHERE id=?",
            (image_id,),
        ).fetchone()

        if not image_row:
            raise ValueError(f"Image #{image_id} not found.")

        # Check if attached to another entity type
        for col in other_columns:
            if image_row[col]:
                raise ValueError("Image is already attached to another entity.")

        # Check if attached to different entity of same type
        if image_row[target_column] not in (None, entity_id):
            label = _ENTITY_LABELS[entity_type]
            raise ValueError(f"Image is already attached to another {label}.")

        # Build UPDATE: set target column, clear others
        set_parts = [f"{target_column}=?"]
        set_parts.extend(f"{col}=NULL" for col in other_columns)

        cur.execute(
            f"UPDATE images SET {', '.join(set_parts)} WHERE id=?",
            (entity_id, image_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_image(
    entity_type: EntityType,
    entity_id: int,
    image_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Detach an image from an entity.

    Args:
        entity_type: One of 'trade', 'analysis_stage', 'setup', 'note'
        entity_id: ID of the entity to detach from
        image_id: ID of the image to detach
        conn: Optional database connection
    """
    if entity_type not in _ENTITY_COLUMNS:
        raise ValueError(f"Unknown entity type: {entity_type}")

    column = _ENTITY_COLUMNS[entity_type]

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE images SET {column}=NULL WHERE {column}=? AND id=?",
            (entity_id, image_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


# =====================================================================
# Wrapper functions
# =====================================================================


def attach_image_to_trade(
    trade_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach image to trade. Wrapper for attach_image()."""
    attach_image("trade", trade_id, image_id, conn=conn)


def detach_image_from_trade(
    trade_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach image from trade. Wrapper for detach_image()."""
    detach_image("trade", trade_id, image_id, conn=conn)


def attach_image_to_analysis_stage(
    stage_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach image to analysis stage. Wrapper for attach_image()."""
    attach_image("analysis_stage", stage_id, image_id, conn=conn)


def detach_image_from_analysis_stage(
    stage_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach image from analysis stage. Wrapper for detach_image()."""
    detach_image("analysis_stage", stage_id, image_id, conn=conn)


def attach_image_to_setup(
    setup_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach image to setup. Wrapper for attach_image()."""
    attach_image("setup", setup_id, image_id, conn=conn)


def detach_image_from_setup(
    setup_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach image from setup. Wrapper for detach_image()."""
    detach_image("setup", setup_id, image_id, conn=conn)


def attach_image_to_note(
    note_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Attach image to note. Wrapper for attach_image()."""
    attach_image("note", note_id, image_id, conn=conn)


def detach_image_from_note(
    note_id: int, image_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Detach image from note. Wrapper for detach_image()."""
    detach_image("note", note_id, image_id, conn=conn)
