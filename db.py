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


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Ensure new columns exist for backward compatibility."""
    _ensure_column(conn, "trades", "estimation INTEGER")
    _ensure_column(conn, "trades", "emotional_problems TEXT")
    _ensure_column(
        conn,
        "notes",
        "category TEXT DEFAULT 'general' CHECK (category IN ('general','observation','review'))",
    )

# =====================================================================
# Schema (built from constants)
# =====================================================================


SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

-- =========================
-- CORE
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
    body        TEXT,
    tags        TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS charts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    asset        TEXT,
    timeframe    TEXT,
    chart_url    TEXT NOT NULL,
    description  TEXT,
    created_at   TEXT
);

-- =========================
-- ANALYSES
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
-- TRADES
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
-- JUNCTIONS (many-to-many)
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
-- INDEXES
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
        _run_migrations(conn)
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
            "INSERT INTO notes (title, body, tags, created_at) VALUES (?, ?, ?, ?)",
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
            SET title=?, body=?, tags=?
            WHERE id=?
            """,
            (title, body, tags, note_id)
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


def _require_section(section: Optional[str]) -> str:
    if section is None:
        raise ValueError("section is required for this operation.")
    if section not in ANALYSIS_SECTIONS:
        raise ValueError(f"section must be one of: {ANALYSIS_SECTIONS}")
    return section


def add_chart(chart_url: str, description: Optional[str] = None) -> int:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO charts (chart_url, description, created_at) "
            "VALUES (?, ?, ?)",
            (chart_url, description, _now_iso_utc())
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


def link_chart_to_trade(trade_id: int, chart_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO trade_charts (trade_id, chart_id) VALUES (?, ?)",
            (trade_id, chart_id)
        )
        conn.commit()
    finally:
        conn.close()


def unlink_chart_from_trade(trade_id: int, chart_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM trade_charts WHERE trade_id=? AND chart_id=?",
            (trade_id, chart_id)
        )
        conn.commit()
    finally:
        conn.close()


def link_note_to_trade(trade_id: int, note_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO trade_notes (trade_id, note_id) VALUES (?, ?)",
            (trade_id, note_id)
        )
        conn.commit()
    finally:
        conn.close()


def unlink_note_from_trade(trade_id: int, note_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM trade_notes WHERE trade_id=? AND note_id=?",
            (trade_id, note_id)
        )
        conn.commit()
    finally:
        conn.close()


def list_charts_for_trade(trade_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.* FROM charts c
            JOIN trade_charts tc ON tc.chart_id = c.id
            WHERE tc.trade_id = ?
            ORDER BY c.id ASC
        """, (trade_id,)).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def delete_chart_if_unused(chart_id: int) -> None:
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM trade_charts WHERE chart_id=?) +
                (SELECT COUNT(*) FROM analysis_charts WHERE chart_id=?) AS cnt
        """, (chart_id, chart_id)).fetchone()
        if row and row[0] == 0:
            conn.execute("DELETE FROM charts WHERE id=?", (chart_id,))
            conn.commit()
    finally:
        conn.close()


def replace_trade_charts(trade_id: int, charts: List[Dict[str, Any]]) -> None:
    existing = list_charts_for_trade(trade_id)
    for chart in existing:
        unlink_chart_from_trade(trade_id, chart["id"])
        delete_chart_if_unused(chart["id"])

    for chart in charts:
        chart_url = (chart.get("chart_url") or "").strip()
        if not chart_url:
            continue
        chart_id = add_chart(chart_url=chart_url,
                             description=chart.get("description"))
        link_chart_to_trade(trade_id, chart_id)


def list_notes_for_trade(trade_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        query = """
            SELECT n.* FROM notes n
            JOIN trade_notes tn ON tn.note_id = n.id
            WHERE tn.trade_id = ?
        """
        params: List[Any] = [trade_id]
        query += " ORDER BY n.id ASC"
        rows = conn.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def replace_trade_notes(trade_id: int, notes: List[Dict[str, Any]]) -> None:
    existing_notes = {
        note["id"]: note for note in list_notes_for_trade(trade_id)
    }
    kept_ids = set()

    for note in notes:
        body = (note.get("body") or "").strip()
        title = (note.get("title") or "").strip() or None
        tags = (note.get("tags") or "").strip() or None
        if not body:
            continue
        raw_id = note.get("id")
        try:
            note_id = int(
                raw_id) if raw_id is not None and raw_id != "" else None
        except (TypeError, ValueError):
            note_id = None

        if note_id and note_id in existing_notes:
            update_note(note_id, title, body, tags=tags)
            link_note_to_trade(trade_id, note_id)
            kept_ids.add(note_id)
        else:
            new_id = add_note(title, body, tags=tags)
            link_note_to_trade(trade_id, new_id)
            kept_ids.add(new_id)

    for note_id in list(existing_notes.keys()):
        if note_id not in kept_ids:
            unlink_note_from_trade(trade_id, note_id)
            delete_note(note_id)


def link_chart_to_analysis(analysis_id: int, chart_id: int, section: str) -> None:
    section_value = _require_section(section)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO analysis_charts (analysis_id, chart_id, section) "
            "VALUES (?, ?, ?)",
            (analysis_id, chart_id, section_value)
        )
        conn.commit()
    finally:
        conn.close()


def link_note_to_analysis(analysis_id: int, note_id: int, section: str) -> None:
    section_value = _require_section(section)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO analysis_notes (analysis_id, note_id, section) "
            "VALUES (?, ?, ?)",
            (analysis_id, note_id, section_value)
        )
        conn.commit()
    finally:
        conn.close()


def list_charts_for_analysis(analysis_id: int,
                             section: Optional[str] = None) -> List[Dict[str, Any]]:
    params: List[Any] = [analysis_id]
    section_filter = ""
    if section:
        if section not in ANALYSIS_SECTIONS:
            raise ValueError(f"section must be one of: {ANALYSIS_SECTIONS}")
        section_filter = " AND ac.section = ?"
        params.append(section)

    conn = get_conn()
    try:
        rows = conn.execute(f"""
            SELECT c.*, ac.section FROM charts c
            JOIN analysis_charts ac ON ac.chart_id = c.id
            WHERE ac.analysis_id = ?{section_filter}
            ORDER BY c.id ASC
        """, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def list_notes_for_analysis(analysis_id: int,
                            section: Optional[str] = None) -> List[Dict[str, Any]]:
    params: List[Any] = [analysis_id]
    section_filter = ""
    if section:
        if section not in ANALYSIS_SECTIONS:
            raise ValueError(f"section must be one of: {ANALYSIS_SECTIONS}")
        section_filter = " AND an.section = ?"
        params.append(section)

    conn = get_conn()
    try:
        rows = conn.execute(f"""
            SELECT n.*, an.section FROM notes n
            JOIN analysis_notes an ON an.note_id = n.id
            WHERE an.analysis_id = ?{section_filter}
            ORDER BY n.id ASC
        """, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def link_chart_to_setup(setup_id: int, chart_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO setup_charts (setup_id, chart_id) VALUES (?, ?)",
            (setup_id, chart_id)
        )
        conn.commit()
    finally:
        conn.close()


def list_charts_for_setup(setup_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.* FROM charts c
            JOIN setup_charts sc ON sc.chart_id = c.id
            WHERE sc.setup_id = ?
            ORDER BY c.id ASC
        """, (setup_id,)).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def link_chart_to_note(note_id: int, chart_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO note_charts (note_id, chart_id) VALUES (?, ?)",
            (note_id, chart_id)
        )
        conn.commit()
    finally:
        conn.close()


def list_charts_for_note(note_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.* FROM charts c
            JOIN note_charts nc ON nc.chart_id = c.id
            WHERE nc.note_id = ?
            ORDER BY c.id ASC
        """, (note_id,)).fetchall()
        return _rows_to_dicts(rows)
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
# Trades lifecycle
# =====================================================================


def open_trade(data: Dict[str, Any]) -> int:
    """
    Create trade in 'open' state.
    Common-sense fields to pass: local_tz, date_local, time_local, account_id, asset, risk_pct (+ optional prices).
    """
    if data.get("state") and data["state"] != "open":
        raise ValueError("Initial trade state must be 'open'.")
    if data.get("result") is not None:
        raise ValueError("Result must be NULL when opening a trade.")

    if data.get("session") and data["session"] not in SESSION_VALUES:
        raise ValueError(f"Unknown session value. Allowed: {SESSION_VALUES}")
    if data.get("risk_pct") is None:
        raise ValueError("risk_pct is required when opening a trade.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (
                local_tz, date_local, time_local,
                account_id, setup_id, analysis_id, asset,
                risk_pct, session, state,
                result, net_pnl, risk_reward, reward_percent,
                estimation,
                emotional_problems, hot_thoughts, cold_thoughts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("local_tz"),
            data.get("date_local"),
            data.get("time_local"),
            data.get("account_id"),
            data.get("setup_id"),
            data.get("analysis_id"),
            data.get("asset"),
            float(data.get("risk_pct")) if data.get(
                "risk_pct") is not None else None,
            data.get("session"),
            "open",
            None,  # result
            None,  # net_pnl
            None,  # risk_reward
            None,  # reward_percent
            int(data.get("estimation")) if data.get(
                "estimation") is not None else None,
            _serialize_emotional_problems(
                data.get("emotional_problems")
                or data.get("emotional_problem")),
            data.get("hot_thoughts"),
            data.get("cold_thoughts"),
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def close_trade(trade_id: int, outcome: Dict[str, Any]) -> None:
    """
    Close trade from 'open' -> 'closed' with outcome data.
    Requires: result in RESULT_VALUES, net_pnl, risk_reward.
    Optional: reward_percent, closed_at_utc.
    """
    result = outcome.get("result")
    net_pnl = outcome.get("net_pnl")
    rr = outcome.get("risk_reward")

    if result not in RESULT_VALUES:
        raise ValueError(f"result must be one of: {RESULT_VALUES}")
    if net_pnl is None or rr is None:
        raise ValueError(
            "net_pnl and risk_reward are required to close a trade.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT state FROM trades WHERE id=?",
                          (trade_id,)).fetchone()
        if not row:
            raise ValueError(f"Trade #{trade_id} not found.")
        if row[0] != "open":
            raise ValueError(
                f"Trade #{trade_id} can be closed only from 'open' state (current: {row[0]}).")

        cur.execute("""
            UPDATE trades
            SET state='closed',
                closed_at_utc=?,
                result=?,
                net_pnl=?,
                risk_reward=?,
                reward_percent=COALESCE(?, reward_percent)
            WHERE id=?
        """, (
            outcome.get("closed_at_utc") or _now_iso_utc(),
            result,
            float(net_pnl),
            float(rr),
            outcome.get("reward_percent"),
            trade_id
        ))
        conn.commit()
    finally:
        conn.close()


def mark_reviewed(trade_id: int, retrospective_note: Optional[str] = None) -> None:
    """Move closed trade to 'reviewed' state and optionally add retrospective note."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT state FROM trades WHERE id=?",
                          (trade_id,)).fetchone()
        if not row:
            raise ValueError(f"Trade #{trade_id} not found.")
        if row[0] != "closed":
            raise ValueError(
                "Only 'closed' trades can be marked as 'reviewed'.")
        cur.execute("""
            UPDATE trades
            SET state='reviewed',
                retrospective_note=COALESCE(?, retrospective_note)
            WHERE id=?
        """, (retrospective_note, trade_id))
        conn.commit()
    finally:
        conn.close()


def cancel_trade(trade_id: int, note: Optional[str] = None) -> None:
    """Cancel trade from 'open' -> 'cancelled' (result stays NULL)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT state FROM trades WHERE id=?",
                          (trade_id,)).fetchone()
        if not row:
            raise ValueError(f"Trade #{trade_id} not found.")
        if row[0] != "open":
            raise ValueError("Only 'open' trades can be cancelled.")
        cur.execute("""
            UPDATE trades
            SET state='cancelled',
                retrospective_note=COALESCE(?, retrospective_note)
            WHERE id=?
        """, (note, trade_id))
        conn.commit()
    finally:
        conn.close()


def mark_missed(trade_id: int, note: Optional[str] = None) -> None:
    """Mark trade from 'open' -> 'missed' (missed opportunity)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT state FROM trades WHERE id=?",
                          (trade_id,)).fetchone()
        if not row:
            raise ValueError(f"Trade #{trade_id} not found.")
        if row[0] != "open":
            raise ValueError("Only 'open' trades can be marked as 'missed'.")
        cur.execute("""
            UPDATE trades
            SET state='missed',
                retrospective_note=COALESCE(?, retrospective_note)
            WHERE id=?
        """, (note, trade_id))
        conn.commit()
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
