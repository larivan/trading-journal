# db.py — SQLite wrapper for Trade Journal (Python 3.9)
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Справочники вынесены в config.py
from config import (
    ASSETS,
    ANALYSIS_SECTIONS,
    EMOTIONAL_PROBLEMS,
    RESULT_VALUES,
    SESSION_VALUES,
    STATE_VALUES,
)

# =====================================================================
# ENUMS / CONSTANTS
# =====================================================================


def _enum_sql(values: List[str]) -> str:
    """Return SQL string for CHECK IN clause:  'a','b','c' """
    return ",".join(f"'{v}'" for v in values)

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

NOTE_CATEGORIES = ("general", "observation", "review")


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


def _now_iso_utc() -> str:
    # ISO-8601 UTC without timezone suffix for SQLite TEXT convenience
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def _serialize_emotional_problems(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                selection = [item for item in parsed
                             if item in EMOTIONAL_PROBLEMS]
                return json.dumps(selection) if selection else None
        except json.JSONDecodeError:
            pass
        selection = [
            item.strip() for item in value.split(",")
            if item.strip() in EMOTIONAL_PROBLEMS
        ]
        return json.dumps(selection) if selection else None
    if isinstance(value, (list, tuple, set)):
        selection = [item for item in value if item in EMOTIONAL_PROBLEMS]
        return json.dumps(selection) if selection else None
    return None


def parse_emotional_problems(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [item for item in parsed if item in EMOTIONAL_PROBLEMS]
        except json.JSONDecodeError:
            pass
        return [
            item.strip() for item in raw.split(",")
            if item.strip() in EMOTIONAL_PROBLEMS
        ]
    if isinstance(raw, (list, tuple)):
        return [item for item in raw if item in EMOTIONAL_PROBLEMS]
    return []


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _ensure_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    column_name = column_def.split()[0]
    if not _column_exists(conn, table, column_name):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

# =====================================================================
# Schema (built from constants)
# =====================================================================


SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

-- =========================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- =========================

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
    body        TEXT
);

CREATE TABLE IF NOT EXISTS charts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_url    TEXT NOT NULL,
    caption      TEXT
);

-- =========================
-- АНАЛИЗЫ
-- =========================

CREATE TABLE IF NOT EXISTS analyses (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at_utc       TEXT,
    local_tz             TEXT,
    date_local           TEXT,
    time_local           TEXT,
    asset                TEXT,
    pre_market_summary   TEXT,
    plan_summary         TEXT,
    post_market_summary  TEXT,
    day_result           TEXT
);

-- =========================
-- СДЕЛКИ
-- =========================

CREATE TABLE IF NOT EXISTS trades (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,

    local_tz           TEXT,
    date_local         TEXT,
    time_local         TEXT,

    account_id         INTEGER,
    setup_id           INTEGER,
    analysis_id        INTEGER,
    asset              TEXT,

    session            TEXT CHECK (session IN ({_enum_sql(SESSION_VALUES)})),

    state              TEXT CHECK (state IN ({_enum_sql(STATE_VALUES)})),
    result             TEXT CHECK (result IN ({_enum_sql(RESULT_VALUES)})),

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
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)  ON DELETE SET NULL   ON UPDATE CASCADE
);

-- =========================
-- СВЯЗИ (отношения многие-ко-многим)
-- =========================

CREATE TABLE IF NOT EXISTS analysis_charts (
    analysis_id  INTEGER,
    chart_id     INTEGER,
    section      TEXT CHECK (section IN ({_enum_sql(ANALYSIS_SECTIONS)})),
    PRIMARY KEY (analysis_id, chart_id, section),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (chart_id)    REFERENCES charts(id)    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS analysis_notes (
    analysis_id  INTEGER,
    note_id      INTEGER,
    section      TEXT CHECK (section IN ({_enum_sql(ANALYSIS_SECTIONS)})),
    PRIMARY KEY (analysis_id, note_id, section),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)     REFERENCES notes(id)    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_charts (
    trade_id  INTEGER,
    chart_id  INTEGER,
    PRIMARY KEY (trade_id, chart_id),
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (chart_id) REFERENCES charts(id)  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_notes (
    trade_id  INTEGER,
    note_id   INTEGER,
    PRIMARY KEY (trade_id, note_id),
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)  REFERENCES notes(id)  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS setup_charts (
    setup_id  INTEGER,
    chart_id  INTEGER,
    PRIMARY KEY (setup_id, chart_id),
    FOREIGN KEY (setup_id) REFERENCES setups(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (chart_id) REFERENCES charts(id)  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS note_charts (
    note_id   INTEGER,
    chart_id  INTEGER,
    PRIMARY KEY (note_id, chart_id),
    FOREIGN KEY (note_id)  REFERENCES notes(id)  ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (chart_id) REFERENCES charts(id)  ON DELETE CASCADE ON UPDATE CASCADE
);

-- =========================
-- ИНДЕКСЫ
-- =========================

CREATE INDEX IF NOT EXISTS idx_trades_date_local   ON trades(date_local);
CREATE INDEX IF NOT EXISTS idx_trades_account      ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_asset        ON trades(asset);
CREATE INDEX IF NOT EXISTS idx_trades_result       ON trades(result);
CREATE INDEX IF NOT EXISTS idx_trades_setup        ON trades(setup_id);

CREATE INDEX IF NOT EXISTS idx_analyses_date_local ON analyses(date_local);
CREATE INDEX IF NOT EXISTS idx_analyses_asset      ON analyses(asset);
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
# Notes
# =====================================================================


def add_note(title: Optional[str], body: str,
             tags: Optional[str] = None,
             category: Optional[str] = None) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (title, body) VALUES (?, ?)",
            (title, body, tags, _now_iso_utc())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_note(note_id: int, title: Optional[str], body: str,
                tags: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE notes
            SET title=?, body=?
            WHERE id=?
            """,
            (title, body, note_id)
        )
        if cur.rowcount == 0:
            raise ValueError(f"Заметка #{note_id} не найдена.")
        conn.commit()
    finally:
        conn.close()


def delete_note(note_id: int) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
    finally:
        conn.close()


def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM notes WHERE id=?",
                           (note_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# =====================================================================
# Charts
# =====================================================================


def add_chart(chart_url: str, caption: Optional[str] = None) -> int:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO charts (chart_url, caption) "
            "VALUES (?, ?)",
            (chart_url, caption, _now_iso_utc())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_chart(chart_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM charts WHERE id=?",
                           (chart_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# =====================================================================
# Analyses
# =====================================================================


def add_analysis(data: Dict[str, Any]) -> int:
    """
    data keys: created_at_utc, local_tz, date_local, time_local, asset,
               pre_market_summary, plan_summary, post_market_summary
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO analyses (
                created_at_utc, local_tz, date_local, time_local,
                pre_market_summary, plan_summary, post_market_summary, asset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("created_at_utc") or _now_iso_utc(),
            data.get("local_tz"),
            data.get("date_local"),
            data.get("time_local"),
            data.get("pre_market_summary"),
            data.get("plan_summary"),
            data.get("post_market_summary"),
            data.get("asset"),
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_analysis(analysis_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM analyses WHERE id=?",
                           (analysis_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_analysis() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY date_local DESC, time_local DESC, id DESC"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
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


def _normalize_trade_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in WRITABLE_TRADE_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if key == "estimation" and value is not None:
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError("estimation должно быть целым числом.")
        if key == "emotional_problems":
            value = _serialize_emotional_problems(value)
        payload[key] = value
    return payload


def create_trade(data: Dict[str, Any]) -> int:
    payload = _normalize_trade_payload(data)
    if not payload:
        raise ValueError("Нет данных для создания сделки.")

    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    values = list(payload.values())

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO trades ({columns}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_trade(trade_id: int, data: Dict[str, Any]) -> None:
    payload = _normalize_trade_payload(data)
    if not payload:
        return

    assignments = ", ".join(f"{col}=?" for col in payload.keys())
    values = list(payload.values())

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE trades SET {assignments} WHERE id=?",
            values + [trade_id],
        )
        if cur.rowcount == 0:
            raise ValueError(f"Сделка #{trade_id} не найдена.")
        conn.commit()
    finally:
        conn.close()


def delete_trade(trade_id: int) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades WHERE id=?", (trade_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Сделка #{trade_id} не найдена.")
        conn.commit()
    finally:
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
        q += " ORDER BY date_local ASC, id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(q, p).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def seed_test_trades(count: int = 10) -> None:
    """
    Insert synthetic trades for manual testing/demo purposes.
    Creates `count` rows with alternating states/results.
    """
    if count <= 0:
        return

    sessions = SESSION_VALUES or ["Other"]
    now = datetime.utcnow()

    conn = get_conn()
    try:
        cur = conn.cursor()
        for idx in range(count):
            opened_at = now - timedelta(hours=idx * 6)
            is_closed = idx % 3 != 0  # roughly 2/3 closed
            is_reviewed = is_closed and idx % 5 == 0

            state = "reviewed" if is_reviewed else (
                "closed" if is_closed else "open")
            result = RESULT_VALUES[idx %
                                   len(RESULT_VALUES)] if is_closed else None
            net_pnl = float((idx + 1) * 50) if is_closed else None
            risk_reward = round(1.0 + (idx % 4) * 0.5,
                                2) if is_closed else None
            reward_percent = round(
                risk_reward * 10, 2) if risk_reward else None
            estimation = None
            problems = []
            if idx % 2 == 0:
                problems.append(EMOTIONAL_PROBLEMS[0]
                                if EMOTIONAL_PROBLEMS else "emotional management")
            if idx % 3 == 0 and len(EMOTIONAL_PROBLEMS) > 1:
                problems.append(EMOTIONAL_PROBLEMS[1])

            cur.execute("""
                INSERT INTO trades (
                    local_tz, date_local, time_local,
                    account_id, setup_id, analysis_id, asset,
                    risk_pct, session, state,
                    result, net_pnl, risk_reward, reward_percent,
                    estimation,
                    emotional_problems, hot_thoughts, cold_thoughts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "UTC+3",
                opened_at.strftime("%Y-%m-%d"),
                opened_at.strftime("%H:%M:%S"),
                None,  # account_id
                None,  # setup_id
                None,  # analysis_id
                ASSETS[idx % len(ASSETS)] if ASSETS else f"SYMBOL{idx+1}",
                0.5 + (idx % 5) * 0.1,
                sessions[idx % len(sessions)],
                state,
                result,
                net_pnl,
                risk_reward,
                reward_percent,
                estimation,
                json.dumps(problems) if problems else None,
                "Impulse entry" if idx % 2 == 0 else None,
                "Calm review" if idx % 3 == 0 else None
            ))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("DB initialized at:", DB_PATH)
