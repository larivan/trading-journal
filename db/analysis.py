# db/analysis.py — Analysis and Analysis Stages CRUD operations
import sqlite3
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from config import ANALYSIS_STATE_VALUES
from db.connection import get_conn, _managed_conn, _rows_to_dicts


ANALYSIS_COLUMNS = [
    "id",
    "date_local",
    "asset",
    "daily_bias",
    "fact_bias",
    "day_result",
    "state",
]

ANALYSIS_WRITABLE_FIELDS = [
    "date_local",
    "asset",
    "daily_bias",
    "fact_bias",
    "day_result",
    "state",
]

ANALYSIS_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "asset": "asset",
    "daily_bias": "daily_bias",
    "fact_bias": "fact_bias",
    "day_result": "day_result",
    "state": "state",
}

ANALYSIS_STAGE_COLUMNS = [
    "s.id AS id",
    "s.analysis_id",
    "a.date_local AS date_local",
    "a.asset AS asset",
    "a.day_result AS day_result",
    "a.daily_bias AS daily_bias",
    "a.fact_bias AS fact_bias",
    "s.time_local",
    "s.type",
    "s.summary",
]

ANALYSIS_STAGE_WRITABLE_FIELDS = [
    "analysis_id",
    "time_local",
    "type",
    "summary",
]

ANALYSIS_STAGE_ORDER_COLUMNS = {
    "id": "s.id",
    "analysis_id": "s.analysis_id",
    "date_local": "a.date_local",
    "time_local": "s.time_local",
    "type": "s.type",
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
        if key == "date_local" and isinstance(value, date):
            payload[key] = value.isoformat()
            continue
        if key == "state" and value not in ANALYSIS_STATE_VALUES:
            raise ValueError(
                f"state должно быть одним из: {', '.join(ANALYSIS_STATE_VALUES)}"
            )
        payload[key] = value
    return payload


def _normalize_analysis_stage_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in ANALYSIS_STAGE_WRITABLE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            payload[key] = None
            continue
        if key == "analysis_id":
            try:
                payload[key] = int(value)
            except (TypeError, ValueError):
                raise ValueError("analysis_id должно быть целым числом.")
            continue
        if key == "time_local":
            if isinstance(value, time):
                payload[key] = value.strftime("%H:%M:%S")
            elif isinstance(value, datetime):
                payload[key] = value.strftime("%H:%M:%S")
            else:
                payload[key] = value
            continue
        if key == "type" and value not in ANALYSIS_STATE_VALUES:
            raise ValueError(
                f"type должно быть одним из: {', '.join(ANALYSIS_STATE_VALUES)}"
            )
        payload[key] = value
    return payload


# =====================================================================
# Analysis (daily overview)
# =====================================================================


def add_analysis(
    data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> int:
    payload = _normalize_analysis_payload(data)
    if "date_local" not in payload:
        raise ValueError("date_local обязательно для анализа.")

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
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = False,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(ANALYSIS_COLUMNS)
    q = f"SELECT {select_clause} FROM analysis WHERE 1=1"
    params: List[Any] = []

    mapping = {
        "asset": "asset",
        "daily_bias": "daily_bias",
        "fact_bias": "fact_bias",
        "day_result": "day_result",
        "state": "state",
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


def get_analysis(analysis_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {', '.join(ANALYSIS_COLUMNS)} FROM analysis WHERE id=?",
            (analysis_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_analysis(
    analysis_id: int, data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
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
            f"UPDATE analysis SET {assignments} WHERE id=?",
            values + [analysis_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Анализ #{analysis_id} не найден.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_analysis(
    analysis_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis WHERE id=?", (analysis_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Анализ #{analysis_id} не найден.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


# =====================================================================
# Analysis stages
# =====================================================================


def add_analysis_stage(
    data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> int:
    payload_data = dict(data or {})
    if not payload_data.get("time_local"):
        payload_data["time_local"] = datetime.now()
    payload = _normalize_analysis_stage_payload(payload_data)
    if not payload:
        raise ValueError("Нет данных для создания этапа анализа.")

    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO analysis_stages ({columns}) VALUES ({placeholders})",
            values,
        )
        if own:
            conn.commit()
        return cur.lastrowid
    finally:
        if own:
            conn.close()


def get_analysis_stage(stage_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {', '.join(ANALYSIS_STAGE_COLUMNS)} "
            "FROM analysis_stages s "
            "JOIN analysis a ON a.id = s.analysis_id "
            "WHERE s.id=?",
            (stage_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_analysis_stages(
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = False,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(ANALYSIS_STAGE_COLUMNS)
    q = (
        f"SELECT {select_clause} "
        "FROM analysis_stages s "
        "JOIN analysis a ON a.id = s.analysis_id "
        "WHERE 1=1"
    )
    params: List[Any] = []

    mapping = {
        "analysis_id": "s.analysis_id",
        "type": "s.type",
        "date_from": "a.date_local >= ?",
        "date_to": "a.date_local <= ?",
        "date_local": "a.date_local",
        "asset": "a.asset",
        "day_result": "a.day_result",
        "daily_bias": "a.daily_bias",
        "fact_bias": "a.fact_bias",
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
        if order_by not in ANALYSIS_STAGE_ORDER_COLUMNS:
            raise ValueError(
                f"order_by must be one of: {sorted(ANALYSIS_STAGE_ORDER_COLUMNS)}"
            )
        q += (
            f" ORDER BY {ANALYSIS_STAGE_ORDER_COLUMNS[order_by]} "
            f"{'ASC' if ascending else 'DESC'}"
        )
    else:
        q += " ORDER BY a.date_local DESC, s.time_local DESC, s.id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(q, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def update_analysis_stage(
    stage_id: int, data: Dict[str, Any], *, conn: Optional[sqlite3.Connection] = None
) -> None:
    payload = _normalize_analysis_stage_payload(data)
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE analysis_stages SET {assignments} WHERE id=?",
            values + [stage_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Этап анализа #{stage_id} не найден.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def delete_analysis_stage(
    stage_id: int, *, conn: Optional[sqlite3.Connection] = None
) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis_stages WHERE id=?", (stage_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Этап анализа #{stage_id} не найден.")
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()
