SCHEMA_VERSION = 1
SNAPSHOT_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL,
    market_title TEXT NOT NULL,
    outcome_label TEXT NOT NULL,
    state TEXT NOT NULL,
    exposure REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    reference_event_id TEXT,
    last_event_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_state (
    session_date TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    stop_reason TEXT,
    cautious_until_probe_confirmed INTEGER NOT NULL,
    consecutive_probe_failures INTEGER NOT NULL,
    last_reconcile_at TEXT,
    last_stop_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_risk_state (
    session_date TEXT PRIMARY KEY,
    realized_loss REAL NOT NULL,
    open_risk REAL NOT NULL,
    daily_loss_limit REAL NOT NULL,
    kill_switch_engaged INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dashboard_snapshot (
    snapshot_id INTEGER PRIMARY KEY CHECK (snapshot_id = 1),
    total_capital REAL NOT NULL,
    realized_pnl_today REAL NOT NULL,
    unrealized_pnl_today REAL NOT NULL,
    realized_pnl_week REAL NOT NULL,
    realized_pnl_month REAL NOT NULL,
    open_positions_count INTEGER NOT NULL,
    session_status TEXT NOT NULL,
    runtime_mode TEXT NOT NULL,
    validation_stage TEXT NOT NULL,
    last_stop_reason TEXT,
    last_reconcile_at TEXT,
    kill_switch_engaged INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    snapshot_version INTEGER NOT NULL
);
"""
