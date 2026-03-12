# ============================================================
# GEM Protocol v3 — Cache Store (SQLite)
# ============================================================
"""
Stores pre-computed engine results in SQLite so that
Streamlit only reads from DB — no live computation on page load.

Tables:
  engine_results  — keyed by (engine, group), stores latest JSON result
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gem_protocol.db"

# Engine group keys
FAST_SIGNALS = "FAST_SIGNALS"      # tether, dollar, dxy, fx_split
SLOW_STOCKS = "SLOW_STOCKS"        # screened stocks + AI analysis
WAREHOUSE = "WAREHOUSE"            # LAA rebalancing


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS engine_results ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  engine VARCHAR(30) NOT NULL,"
        "  timestamp DATETIME NOT NULL,"
        "  result_json TEXT NOT NULL,"
        "  status VARCHAR(20)"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_engine_ts "
        "ON engine_results(engine, timestamp DESC)"
    )
    conn.commit()
    return conn


def save_result(engine: str, data: dict) -> None:
    """Insert a new result row for the given engine group."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO engine_results (engine, timestamp, result_json, status) "
            "VALUES (?, ?, ?, ?)",
            (
                engine,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(data, ensure_ascii=False, default=str),
                "ok",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_latest(engine: str, max_age_seconds: int = 600) -> dict | None:
    """Load the most recent result for *engine* if it's within max_age_seconds.

    Returns None if no result or result is stale.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT timestamp, result_json FROM engine_results "
            "WHERE engine = ? ORDER BY timestamp DESC LIMIT 1",
            (engine,),
        ).fetchone()
        if not row:
            return None
        ts_str, payload = row
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > max_age_seconds:
            return None
        return json.loads(payload)
    finally:
        conn.close()


def cleanup_old(engine: str, keep: int = 100) -> None:
    """Keep only the latest *keep* rows for an engine group."""
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM engine_results WHERE engine = ? AND id NOT IN "
            "(SELECT id FROM engine_results WHERE engine = ? "
            " ORDER BY timestamp DESC LIMIT ?)",
            (engine, engine, keep),
        )
        conn.commit()
    finally:
        conn.close()
