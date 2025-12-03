# db.py — SQLite wrapper for Trade Journal (Python 3.9)
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Union

# Справочники вынесены в config.py
from config import (
    ANALYSIS_STATE_VALUES
)

# =====================================================================
# Paths & helpers
# =====================================================================


TRADE_ORDER_COLUMNS = {
    "id",
    "date_local",
    "time_local",
    "account_id",
    "setup_id",
    "analysis_id",
    "asset",
    "state",
    "result",
    "session",
    "net_pnl",
    "risk_reward",
    "reward_percent",
}

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

ANALYSIS_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "asset": "asset",
    "daily_bias": "daily_bias",
    "fact_bias": "fact_bias",
    "day_result": "day_result",
    "state": "state",
}

ANALYSIS_STAGE_ORDER_COLUMNS = {
    "id": "s.id",
    "analysis_id": "s.analysis_id",
    "date_local": "a.date_local",
    "time_local": "s.time_local",
    "type": "s.type",
}

NOTE_ORDER_COLUMNS = {
    "id": "id",
    "date_local": "date_local",
    "time_local": "time_local",
    "title": "title",
    "note_type": "note_type",
}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "journal.db")


def _ensure_dirs() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _managed_conn(conn: Optional[sqlite3.Connection]) -> tuple[sqlite3.Connection, bool]:
    """Возвращает соединение и флаг владения (нужно ли закрывать/коммитить)."""
    if conn is None:
        return get_conn(), True
    return conn, False


@contextmanager
def transaction(conn: Optional[sqlite3.Connection] = None):
    """Контекст для атомарных операций: BEGIN/COMMIT/ROLLBACK + управление conn."""
    connection, own = _managed_conn(conn)
    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if own:
            connection.close()


def _now_iso_utc() -> str:
    # ISO-8601 UTC without timezone suffix for SQLite TEXT convenience
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


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
# Schema (built from constants)
# =====================================================================


SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

-- =========================
-- ТАБЛИЦЫ
-- =========================

CREATE TABLE IF NOT EXISTS analysis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_local  TEXT NOT NULL,
    asset       TEXT,
    daily_bias  TEXT,
    fact_bias   TEXT,
    day_result  TEXT,
    state       TEXT
);

CREATE TABLE IF NOT EXISTS analysis_stages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id  INTEGER NOT NULL,
    time_local   TEXT,
    type         TEXT,
    summary      TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS trades (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    local_tz           TEXT NOT NULL,
    date_local         TEXT NOT NULL,
    time_local         TEXT NOT NULL,
    account_id         INTEGER,
    setup_id           INTEGER,
    analysis_id        INTEGER,
    asset              TEXT NOT NULL,
    session            TEXT NOT NULL,
    state              TEXT NOT NULL,
    result             TEXT,
    net_pnl            REAL,
    risk_pct           REAL,
    risk_reward        REAL,
    reward_percent     REAL,
    estimation         INTEGER,
    emotional_problems TEXT,
    hot_thoughts       TEXT,
    cold_thoughts      TEXT,
    
    FOREIGN KEY (account_id)  REFERENCES accounts(id)  ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (setup_id)    REFERENCES setups(id)    ON DELETE SET NULL   ON UPDATE CASCADE,
    FOREIGN KEY (analysis_id) REFERENCES analysis(id)  ON DELETE SET NULL   ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS accounts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    broker            TEXT,
    currency          TEXT DEFAULT 'USD',
    starting_balance  REAL,
    is_prop           INTEGER DEFAULT 0,
    created_at        TEXT,
    archived          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS setups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    body        TEXT,
    date_local  TEXT,
    time_local  TEXT,
    note_type   TEXT
);

CREATE TABLE IF NOT EXISTS charts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_url         TEXT NOT NULL,
    caption           TEXT,
    trade_id          INTEGER,
    analysis_stage_id INTEGER,
    setup_id          INTEGER,
    CHECK (
        (CASE WHEN trade_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN analysis_stage_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN setup_id IS NOT NULL THEN 1 ELSE 0 END)
        <= 1
    ),
    FOREIGN KEY (trade_id)          REFERENCES trades(id)           ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (analysis_stage_id) REFERENCES analysis_stages(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (setup_id)          REFERENCES setups(id)          ON DELETE CASCADE ON UPDATE CASCADE
);

-- =========================
-- СВЯЗИ (отношения многие-ко-многим)
-- =========================

CREATE TABLE IF NOT EXISTS analysis_notes (
    analysis_stage_id INTEGER,
    note_id           INTEGER,
    PRIMARY KEY (analysis_stage_id, note_id),
    FOREIGN KEY (analysis_stage_id) REFERENCES analysis_stages(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)           REFERENCES notes(id)           ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_notes (
    trade_id  INTEGER,
    note_id   INTEGER,
    PRIMARY KEY (trade_id, note_id),
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)  REFERENCES notes(id)  ON DELETE CASCADE ON UPDATE CASCADE
);

-- =========================
-- ИНДЕКСЫ
-- =========================

CREATE INDEX IF NOT EXISTS idx_trades_date_local   ON trades(date_local);
CREATE INDEX IF NOT EXISTS idx_trades_account      ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_asset        ON trades(asset);
CREATE INDEX IF NOT EXISTS idx_trades_result       ON trades(result);
CREATE INDEX IF NOT EXISTS idx_trades_setup        ON trades(setup_id);

CREATE INDEX IF NOT EXISTS idx_analysis_date_local         ON analysis(date_local);
CREATE INDEX IF NOT EXISTS idx_analysis_asset              ON analysis(asset);
CREATE INDEX IF NOT EXISTS idx_analysis_stages_analysis_id ON analysis_stages(analysis_id);
CREATE INDEX IF NOT EXISTS idx_charts_trade_id             ON charts(trade_id);
CREATE INDEX IF NOT EXISTS idx_charts_analysis_stage_id    ON charts(analysis_stage_id);
CREATE INDEX IF NOT EXISTS idx_charts_setup_id             ON charts(setup_id);
"""


def init_db() -> None:
    """Create DB schema if not exists."""
    _ensure_dirs()
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

# =====================================================================
# Accounts & Setups
# =====================================================================


def create_account(name: str, broker: Optional[str] = None,
                   currency: str = "USD",
                   starting_balance: Optional[float] = None,
                   is_prop: int = 0) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO accounts (name, broker, currency, starting_balance, is_prop, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, broker, currency, starting_balance, is_prop, _now_iso_utc())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_accounts() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE archived IS NULL OR archived=0 ORDER BY id ASC"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def create_setup(name: str, description: Optional[str] = None) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO setups (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, _now_iso_utc())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_setups() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM setups ORDER BY name ASC").fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()

# =====================================================================
# Analysis (daily overview)
# =====================================================================


def add_analysis(data: Dict[str, Any],
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> int:
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


def list_analysis(filters: Optional[Dict[str, Any]] = None,
                  order_by: Optional[str] = None,
                  ascending: bool = False) -> List[Dict[str, Any]]:
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
                f"order_by must be one of: {sorted(ANALYSIS_ORDER_COLUMNS)}")
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


def update_analysis(analysis_id: int, data: Dict[str, Any],
                    *,
                    conn: Optional[sqlite3.Connection] = None) -> None:
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


def delete_analysis(analysis_id: int,
                    *,
                    conn: Optional[sqlite3.Connection] = None) -> None:
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
# Charts
# =====================================================================


def add_chart(chart_url: str, caption: Optional[str] = None,
              *,
              conn: Optional[sqlite3.Connection] = None) -> int:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO charts (chart_url, caption) "
            "VALUES (?, ?)",
            (chart_url, caption)
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


def update_chart(chart_id: int, chart_url: str,
                 caption: Optional[str] = None,
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> None:
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


def delete_chart(chart_id: int,
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM charts WHERE id=?", (chart_id,))
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def list_charts(*,
                trade_id: Optional[int] = None,
                analysis_stage_id: Optional[int] = None,
                setup_id: Optional[int] = None,
                unattached: bool = False) -> List[Dict[str, Any]]:
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
    if unattached:
        conditions.append("trade_id IS NULL")
        conditions.append("analysis_stage_id IS NULL")
        conditions.append("setup_id IS NULL")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM charts {where_clause} ORDER BY id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def attach_chart_to_trade(trade_id: int, chart_id: int,
                          *,
                          conn: Optional[sqlite3.Connection] = None) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["analysis_stage_id"] or chart_row["setup_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["trade_id"] not in (None, trade_id):
            raise ValueError("Чарт уже привязан к другой сделке.")
        cur.execute(
            "UPDATE charts SET trade_id=?, analysis_stage_id=NULL, setup_id=NULL WHERE id=?",
            (trade_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_trade(trade_id: int, chart_id: int,
                            *,
                            conn: Optional[sqlite3.Connection] = None) -> None:
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


def attach_chart_to_analysis_stage(stage_id: int, chart_id: int,
                                   *,
                                   conn: Optional[sqlite3.Connection] = None) -> None:
    conn, own = _managed_conn(conn)
    try:
        cur = conn.cursor()
        chart_row = cur.execute(
            "SELECT id, trade_id, analysis_stage_id, setup_id FROM charts WHERE id=?",
            (chart_id,),
        ).fetchone()
        if not chart_row:
            raise ValueError(f"Чарт #{chart_id} не найден.")
        if chart_row["trade_id"] or chart_row["setup_id"]:
            raise ValueError("Чарт уже привязан к другой сущности.")
        if chart_row["analysis_stage_id"] not in (None, stage_id):
            raise ValueError("Чарт уже привязан к другому этапу анализа.")
        cur.execute(
            "UPDATE charts SET analysis_stage_id=?, trade_id=NULL, setup_id=NULL WHERE id=?",
            (stage_id, chart_id),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def detach_chart_from_analysis_stage(stage_id: int, chart_id: int,
                                     *,
                                     conn: Optional[sqlite3.Connection] = None) -> None:
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

# =====================================================================
# Analysis stages
# =====================================================================


def add_analysis_stage(data: Dict[str, Any],
                       *,
                       conn: Optional[sqlite3.Connection] = None) -> int:
    payload = _normalize_analysis_stage_payload(data)
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


def list_analysis_stages(filters: Optional[Dict[str, Any]] = None,
                         order_by: Optional[str] = None,
                         ascending: bool = False) -> List[Dict[str, Any]]:
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
                f"order_by must be one of: {sorted(ANALYSIS_STAGE_ORDER_COLUMNS)}")
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


def update_analysis_stage(stage_id: int, data: Dict[str, Any],
                          *,
                          conn: Optional[sqlite3.Connection] = None) -> None:
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


def delete_analysis_stage(stage_id: int,
                          *,
                          conn: Optional[sqlite3.Connection] = None) -> None:
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


# =====================================================================
# Trade queries
# =====================================================================

def get_trade_by_id(trade_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM trades WHERE id=?",
                           (trade_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


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
    "result",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "estimation",
    "emotional_problems",
    "hot_thoughts",
    "cold_thoughts",
]


def create_trade(data: Dict[str, Any],
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> int:
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


def update_trade(trade_id: int, data: Dict[str, Any],
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> None:
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


def delete_trade(trade_id: int,
                 *,
                 conn: Optional[sqlite3.Connection] = None) -> None:
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
    "result",
    "net_pnl",
    "risk_reward",
    "reward_percent",
    "estimation",
    "emotional_problems",
    "hot_thoughts",
    "cold_thoughts",
]

TRADE_COMPAT_COLUMNS = [
    "result AS trade_result",
    "risk_reward AS rr",
    "net_pnl AS pnl",
    "date_local AS trade_date",
    "time_local AS open_time",
]


def list_trades(filters: Optional[Dict[str, Any]] = None,
                order_by: Optional[str] = None,
                ascending: bool = True) -> List[Dict[str, Any]]:
    filters = filters or {}
    select_clause = ", ".join(TRADE_COLUMNS + TRADE_COMPAT_COLUMNS)
    q = f"SELECT {select_clause} FROM trades WHERE 1=1"
    p: List[Any] = []

    mapping = {
        "account_id": "account_id",
        "asset": "asset",
        "setup_id": "setup_id",
        "analysis_id": "analysis_id",
        "state": "state",
        "result": "result",
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


if __name__ == "__main__":
    init_db()
    print("DB initialized at:", DB_PATH)
