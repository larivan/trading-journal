# db/connection.py — Connection management and helpers
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List

# =====================================================================
# Paths & helpers
# =====================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("TRADE_JOURNAL_DB_PATH", os.path.join(BASE_DIR, "journal.db"))

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
_USE_TURSO = bool(TURSO_URL and TURSO_TOKEN)

if _USE_TURSO:
    try:
        import libsql_experimental as libsql  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "libsql-experimental is required when TURSO_DATABASE_URL is set. "
            "Run: pip install libsql-experimental"
        )

# Thread-local storage: one persistent Turso connection per thread.
# Streamlit reuses threads across requests, so each thread connects once
# instead of on every get_conn() call, eliminating repeated TCP/TLS overhead.
_turso_local = threading.local()


# =====================================================================
# Turso compatibility wrappers
# =====================================================================

class _TursoRow(dict):
    """Dict-compatible row wrapper that converts libsql tuple rows to named dicts.

    Inheriting from dict makes dict(row) work exactly like sqlite3.Row,
    and lets all existing dict(r) / row['col'] patterns work unchanged.
    """

    def __init__(self, description, values):
        super().__init__(zip((d[0] for d in description), values))


class _TursoCursor:
    """Wraps a libsql cursor to match the sqlite3 cursor interface used in this codebase."""

    __slots__ = ("_cur",)

    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql: str, params=None):
        if params is not None:
            self._cur.execute(sql, tuple(params))
        else:
            self._cur.execute(sql)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return _TursoRow(self._cur.description, row)

    def fetchall(self):
        rows = self._cur.fetchall()
        desc = self._cur.description
        return [_TursoRow(desc, r) for r in rows]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description


class _TursoConnection:
    """Wraps a libsql connection to match the sqlite3 connection interface used in this codebase."""

    __slots__ = ("_conn",)

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=None):
        cur = _TursoCursor(self._conn.cursor())
        return cur.execute(sql, params)

    def cursor(self):
        return _TursoCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        pass  # Persistent per-thread connection; closing is a no-op


# =====================================================================
# Connection factory
# =====================================================================

def _ensure_dirs() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def _get_turso_conn() -> "_TursoConnection":
    """Return a cached Turso connection for the current thread, creating it if needed."""
    conn = getattr(_turso_local, "conn", None)
    if conn is None:
        _turso_local.conn = _TursoConnection(libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN))
    return _turso_local.conn


def get_conn():
    if _USE_TURSO:
        return _get_turso_conn()
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _managed_conn(conn) -> tuple:
    """Returns connection and ownership flag (whether to close/commit)."""
    if conn is None:
        return get_conn(), True
    return conn, False


@contextmanager
def transaction(conn=None):
    """Context for atomic operations: BEGIN/COMMIT/ROLLBACK + connection management."""
    connection, own = _managed_conn(conn)
    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass  # не подавляем оригинальное исключение
        raise
    finally:
        if own:
            connection.close()


def _now_iso_utc() -> str:
    """ISO-8601 UTC timestamp without timezone suffix for SQLite TEXT convenience."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _rows_to_dicts(rows: List) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


# =====================================================================
# Schema
# =====================================================================

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- =========================
-- ПОЛЬЗОВАТЕЛИ
-- =========================

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT,
    email         TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL,
    is_active     INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id            INTEGER PRIMARY KEY,
    assets             TEXT    DEFAULT '["EUR/USD","GBP/USD","XAU/USD","XAG/USD"]',
    be_threshold       REAL    DEFAULT 0.05,
    risk_min           REAL    DEFAULT 0.5,
    risk_max           REAL    DEFAULT 2.0,
    local_tz           TEXT    DEFAULT 'Europe/Moscow',
    currency           TEXT    DEFAULT 'USD',
    theme              TEXT    DEFAULT 'light',
    language           TEXT    DEFAULT 'en',
    default_asset      TEXT    DEFAULT NULL,
    default_account_id INTEGER DEFAULT NULL,
    mistake_types      TEXT    DEFAULT '[]',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =========================
-- ТАБЛИЦЫ СУЩНОСТЕЙ
-- =========================

CREATE TABLE IF NOT EXISTS accounts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    name              TEXT NOT NULL,
    broker            TEXT,
    currency          TEXT,
    starting_balance  REAL NOT NULL,
    is_prop           INTEGER DEFAULT 0,
    created_at        TEXT,
    archived          INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS setups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    UNIQUE(name, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    body        TEXT NOT NULL,
    date_local  TEXT NOT NULL,
    time_local  TEXT NOT NULL,
    category    TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analysis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    date_local  TEXT NOT NULL,
    asset       TEXT,
    daily_bias  TEXT,
    fact_bias   TEXT,
    day_result  TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trades (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    local_tz       TEXT NOT NULL,
    date_local     TEXT NOT NULL,
    time_local     TEXT NOT NULL,
    account_id     INTEGER NOT NULL,
    setup_id       INTEGER,
    analysis_id    INTEGER,
    asset          TEXT NOT NULL,
    trade_type     TEXT,
    session        TEXT NOT NULL,
    is_missed      INTEGER DEFAULT 0,
    net_pnl        REAL,
    risk_pct       REAL,
    risk_reward    REAL,
    reward_percent REAL,
    is_correct     INTEGER,
    mistake_types  TEXT,
    FOREIGN KEY (user_id)     REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (account_id)  REFERENCES accounts(id)  ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (setup_id)    REFERENCES setups(id)    ON DELETE SET NULL   ON UPDATE CASCADE,
    FOREIGN KEY (analysis_id) REFERENCES analysis(id)  ON DELETE SET NULL   ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    image_url   TEXT NOT NULL,
    caption     TEXT,
    trade_id    INTEGER,
    analysis_id INTEGER,
    setup_id    INTEGER,
    note_id     INTEGER,
    CHECK (
        (CASE WHEN trade_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN analysis_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN setup_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN note_id IS NOT NULL THEN 1 ELSE 0 END)
        <= 1
    ),
    FOREIGN KEY (trade_id)    REFERENCES trades(id)    ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (analysis_id) REFERENCES analysis(id)  ON DELETE CASCADE,
    FOREIGN KEY (setup_id)    REFERENCES setups(id)    ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (note_id)     REFERENCES notes(id)     ON DELETE CASCADE ON UPDATE CASCADE
);

-- =========================
-- СВЯЗИ (отношения многие-ко-многим)
-- =========================

CREATE TABLE IF NOT EXISTS analysis_notes (
    analysis_id INTEGER NOT NULL,
    note_id     INTEGER NOT NULL,
    PRIMARY KEY (analysis_id, note_id),
    FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE,
    FOREIGN KEY (note_id)     REFERENCES notes(id)    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analysis_notes_analysis ON analysis_notes(analysis_id);

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

CREATE INDEX IF NOT EXISTS idx_trades_user_id    ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_user_id  ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_user_id  ON analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_user_id     ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_setups_user_id    ON setups(user_id);

CREATE INDEX IF NOT EXISTS idx_trades_date_local   ON trades(date_local);
CREATE INDEX IF NOT EXISTS idx_trades_account      ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_asset        ON trades(asset);
CREATE INDEX IF NOT EXISTS idx_trades_setup        ON trades(setup_id);
CREATE INDEX IF NOT EXISTS idx_trades_analysis     ON trades(analysis_id);

CREATE INDEX IF NOT EXISTS idx_analysis_date_local ON analysis(date_local);
CREATE INDEX IF NOT EXISTS idx_analysis_asset      ON analysis(asset);
CREATE INDEX IF NOT EXISTS idx_images_trade_id     ON images(trade_id);
CREATE INDEX IF NOT EXISTS idx_images_setup_id     ON images(setup_id);
CREATE INDEX IF NOT EXISTS idx_images_note_id      ON images(note_id);
CREATE INDEX IF NOT EXISTS idx_images_analysis_id  ON images(analysis_id);
CREATE INDEX IF NOT EXISTS idx_trade_notes_note_id ON trade_notes(note_id);
"""


def _execute_schema(conn) -> None:
    """Execute schema statements one by one (Turso doesn't support executescript)."""
    for raw_stmt in SCHEMA_SQL.split(";"):
        stmt = raw_stmt.strip()
        if not stmt:
            continue
        # Skip fragments that contain only whitespace and comment lines
        meaningful = "\n".join(
            line for line in stmt.split("\n")
            if line.strip() and not line.strip().startswith("--")
        ).strip()
        if meaningful:
            conn.execute(stmt)
    conn.commit()


_DROP_LEGACY_SQL = """
DROP TABLE IF EXISTS analysis_note_links;
DROP TABLE IF EXISTS analysis_stages;
"""


def init_db() -> None:
    """Create DB schema if not exists."""
    if not _USE_TURSO:
        _ensure_dirs()
    conn = get_conn()
    try:
        if _USE_TURSO:
            for stmt in _DROP_LEGACY_SQL.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(s)
            _execute_schema(conn)
        else:
            conn.executescript(_DROP_LEGACY_SQL + SCHEMA_SQL)
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("DB initialized at:", TURSO_URL if _USE_TURSO else DB_PATH)
