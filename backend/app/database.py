"""Async SQLite database management with WAL mode."""

from __future__ import annotations

import aiosqlite
import logging
from pathlib import Path
from app.config import config

logger = logging.getLogger("anomalypulse.database")

_db: aiosqlite.Connection | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metric_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    value REAL NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metric_points_metric_ts
ON metric_points(metric_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metric_points_ts
ON metric_points(timestamp DESC);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id TEXT PRIMARY KEY,
    metric TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    value REAL NOT NULL,
    score REAL NOT NULL,
    detector TEXT NOT NULL,
    severity TEXT NOT NULL,
    is_anomaly INTEGER NOT NULL DEFAULT 1,
    contributing_detectors TEXT NOT NULL DEFAULT '[]',
    context_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_metric_ts
ON anomaly_events(metric, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_severity
ON anomaly_events(severity, timestamp DESC);

CREATE TABLE IF NOT EXISTS alert_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    metric_pattern TEXT NOT NULL,
    rule_type TEXT NOT NULL DEFAULT 'anomaly_score',
    severity TEXT NOT NULL DEFAULT 'warning',
    thresholds_json TEXT NOT NULL DEFAULT '{}',
    cooldown_seconds INTEGER NOT NULL DEFAULT 300,
    actions_json TEXT NOT NULL DEFAULT '["dashboard"]',
    filters_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_metric
ON alert_rules(metric_pattern);

CREATE TABLE IF NOT EXISTS alert_events (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    message TEXT NOT NULL DEFAULT '',
    triggered_at INTEGER NOT NULL,
    resolved_at INTEGER,
    context_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_alert_events_status
ON alert_events(status, severity, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_events_metric
ON alert_events(metric, triggered_at DESC);

CREATE TABLE IF NOT EXISTS detector_configs (
    metric_name TEXT PRIMARY KEY,
    ensemble_mode TEXT NOT NULL DEFAULT 'majority',
    zscore_json TEXT NOT NULL DEFAULT '{}',
    ewma_json TEXT NOT NULL DEFAULT '{}',
    iforest_json TEXT NOT NULL DEFAULT '{}',
    percentile_json TEXT NOT NULL DEFAULT '{}',
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_detector_configs_metric
ON detector_configs(metric_name);
"""


async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(config.db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA synchronous=NORMAL")
        await _db.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await _db.execute("PRAGMA busy_timeout=5000")
        logger.info(f"Database connected: {config.db_path}")
    return _db


async def init_schema() -> None:
    """Create all tables and indexes."""
    db = await get_db()
    await db.executescript(SCHEMA_SQL)
    await db.commit()
    logger.info("Database schema initialized")


async def close_db() -> None:
    """Close database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")
