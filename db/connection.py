# db/connection.py — Connection management and helpers
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# =====================================================================
# Paths & helpers
# =====================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("TRADE_JOURNAL_DB_PATH", os.path.join(BASE_DIR, "journal.db"))


def _ensure_dirs() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _managed_conn(
    conn: Optional[sqlite3.Connection],
) -> tuple[sqlite3.Connection, bool]:
    """Returns connection and ownership flag (whether to close/commit)."""
    if conn is None:
        return get_conn(), True
    return conn, False


@contextmanager
def transaction(conn: Optional[sqlite3.Connection] = None):
    """Context for atomic operations: BEGIN/COMMIT/ROLLBACK + connection management."""
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
    """ISO-8601 UTC timestamp without timezone suffix for SQLite TEXT convenience."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


# =====================================================================
# Schema
# =====================================================================

SCHEMA_SQL = """
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
    account_id         INTEGER NOT NULL,
    setup_id           INTEGER,
    analysis_id        INTEGER,
    asset              TEXT NOT NULL,
    session            TEXT NOT NULL,
    state              TEXT NOT NULL,
    is_missed          INTEGER DEFAULT 0,
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
    currency          TEXT,
    starting_balance  REAL NOT NULL,
    is_prop           INTEGER DEFAULT 0,
    created_at        TEXT,
    archived          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS setups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    body        TEXT NOT NULL,
    date_local  TEXT NOT NULL,
    time_local  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS charts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_url         TEXT NOT NULL,
    caption           TEXT,
    trade_id          INTEGER,
    analysis_stage_id INTEGER,
    setup_id          INTEGER,
    note_id           INTEGER,
    CHECK (
        (CASE WHEN trade_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN analysis_stage_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN setup_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN note_id IS NOT NULL THEN 1 ELSE 0 END)
        <= 1
    ),
    FOREIGN KEY (trade_id)          REFERENCES trades(id)           ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (analysis_stage_id) REFERENCES analysis_stages(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (setup_id)          REFERENCES setups(id)          ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)           REFERENCES notes(id)           ON DELETE CASCADE ON UPDATE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_trades_setup        ON trades(setup_id);
CREATE INDEX IF NOT EXISTS idx_trades_analysis     ON trades(analysis_id);

CREATE INDEX IF NOT EXISTS idx_analysis_date_local         ON analysis(date_local);
CREATE INDEX IF NOT EXISTS idx_analysis_asset              ON analysis(asset);
CREATE INDEX IF NOT EXISTS idx_analysis_stages_analysis_id ON analysis_stages(analysis_id);
CREATE INDEX IF NOT EXISTS idx_charts_trade_id             ON charts(trade_id);
CREATE INDEX IF NOT EXISTS idx_charts_analysis_stage_id    ON charts(analysis_stage_id);
CREATE INDEX IF NOT EXISTS idx_charts_setup_id             ON charts(setup_id);
CREATE INDEX IF NOT EXISTS idx_charts_note_id              ON charts(note_id);
CREATE INDEX IF NOT EXISTS idx_trade_notes_note_id         ON trade_notes(note_id);
CREATE INDEX IF NOT EXISTS idx_analysis_notes_note_id      ON analysis_notes(note_id);
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


if __name__ == "__main__":
    init_db()
    print("DB initialized at:", DB_PATH)
