# db.py — SQLite wrapper for Trade Journal (Python 3.9)
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Справочники вынесены в config.py
from config import (
    ANALYSIS_SECTIONS,
    RESULT_VALUES,
    SESSION_VALUES,
    STATE_VALUES,
    STATUS_VALUES,
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
    "opened_at_utc",
    "closed_at_utc",
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

    opened_at_utc      TEXT,
    closed_at_utc      TEXT,
    local_tz           TEXT,
    date_local         TEXT,
    time_local         TEXT,

    account_id         INTEGER,
    setup_id           INTEGER,
    analysis_id        INTEGER,
    asset              TEXT,

    entry_price        REAL,
    stop_loss          REAL,
    take_profit        REAL,
    position_size      REAL,
    risk_pct           REAL,

    session            TEXT CHECK (session IN ({_enum_sql(SESSION_VALUES)})),

    state              TEXT CHECK (state IN ({_enum_sql(STATE_VALUES)})),
    result             TEXT CHECK (result IN ({_enum_sql(RESULT_VALUES)})),

    net_pnl            REAL,
    risk_reward        REAL,
    reward_percent     REAL,

    status             TEXT CHECK (status IN ({_enum_sql(STATUS_VALUES)})),
    emotional_problem  TEXT,
    hot_thoughts       TEXT,
    cold_thoughts      TEXT,
    retrospective_note TEXT,

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
CREATE INDEX IF NOT EXISTS idx_trades_opened_utc   ON trades(opened_at_utc);

CREATE INDEX IF NOT EXISTS idx_analyses_date_local ON analyses(date_local);
CREATE INDEX IF NOT EXISTS idx_analyses_type       ON analyses(type);
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


def add_note(title: Optional[str], body: str, tags: Optional[str] = None) -> int:
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


def add_chart(title: Optional[str], chart_url: str,
              description: Optional[str] = None) -> int:
    if not chart_url:
        raise ValueError("chart_url is required.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO charts (title, chart_url, description, created_at) "
            "VALUES (?, ?, ?, ?)",
            (title, chart_url, description, _now_iso_utc())
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


def list_notes_for_trade(trade_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT n.* FROM notes n
            JOIN trade_notes tn ON tn.note_id = n.id
            WHERE tn.trade_id = ?
            ORDER BY n.id ASC
        """, (trade_id,)).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


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
            "SELECT * FROM analyses ORDER BY name ASC").fetchall()
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
                opened_at_utc, closed_at_utc,
                local_tz, date_local, time_local,
                account_id, setup_id, analysis_id, asset,
                entry_price, stop_loss, take_profit, position_size,
                risk_pct, session, state,
                result, net_pnl, risk_reward, reward_percent,
                status, emotional_problem, hot_thoughts, cold_thoughts, retrospective_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("opened_at_utc") or _now_iso_utc(),
            None,
            data.get("local_tz"),
            data.get("date_local"),
            data.get("time_local"),
            data.get("account_id"),
            data.get("setup_id"),
            data.get("analysis_id"),
            data.get("asset"),
            data.get("entry_price"),
            data.get("stop_loss"),
            data.get("take_profit"),
            data.get("position_size"),
            float(data.get("risk_pct")) if data.get(
                "risk_pct") is not None else None,
            data.get("session"),
            "open",
            None,  # result
            None,  # net_pnl
            None,  # risk_reward
            None,  # reward_percent
            data.get("status"),
            data.get("emotional_problem"),
            data.get("hot_thoughts"),
            data.get("cold_thoughts"),
            data.get("retrospective_note")
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


def list_trades(filters: Optional[Dict[str, Any]] = None,
                order_by: Optional[str] = None,
                ascending: bool = True) -> List[Dict[str, Any]]:
    filters = filters or {}
    q = "SELECT * FROM trades WHERE 1=1"
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
        q += " ORDER BY date_local ASC, opened_at_utc ASC, id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(q, p).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("DB initialized at:", DB_PATH)
