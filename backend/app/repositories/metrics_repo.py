"""Metrics repository — SQLite persistence for metric points."""

from __future__ import annotations

import json
import time
import logging
from typing import Any

from app.database import get_db
from app.models.schemas import MetricPoint, MetricSummary

logger = logging.getLogger("anomalypulse.repo.metrics")


async def insert_point(point: MetricPoint) -> int:
    """Insert a single metric point. Returns the row id."""
    db = await get_db()
    now_ms = int(time.time() * 1000)
    cursor = await db.execute(
        "INSERT INTO metric_points (metric_name, timestamp, value, tags_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (point.metric_name, point.timestamp, point.value, json.dumps(point.tags), now_ms),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore


async def insert_points_batch(points: list[MetricPoint]) -> int:
    """Insert multiple metric points. Returns count inserted."""
    if not points:
        return 0
    db = await get_db()
    now_ms = int(time.time() * 1000)
    rows = [
        (p.metric_name, p.timestamp, p.value, json.dumps(p.tags), now_ms)
        for p in points
    ]
    await db.executemany(
        "INSERT INTO metric_points (metric_name, timestamp, value, tags_json, created_at) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    await db.commit()
    return len(rows)


async def get_history(
    metric_name: str,
    start: int | None = None,
    end: int | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Get historical points for a metric within a time range."""
    db = await get_db()
    clauses = ["metric_name = ?"]
    params: list[Any] = [metric_name]

    if start is not None:
        clauses.append("timestamp >= ?")
        params.append(start)
    if end is not None:
        clauses.append("timestamp <= ?")
        params.append(end)

    where = " AND ".join(clauses)
    params.append(limit)

    cursor = await db.execute(
        f"SELECT timestamp, value, tags_json FROM metric_points WHERE {where} ORDER BY timestamp DESC LIMIT ?",
        params,
    )
    rows = await cursor.fetchall()
    return [
        {
            "timestamp": row[0],
            "value": row[1],
            "tags": json.loads(row[2]),
        }
        for row in rows
    ]


async def get_latest(metric_name: str) -> dict[str, Any] | None:
    """Get the most recent point for a metric."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT timestamp, value, tags_json FROM metric_points WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 1",
        (metric_name,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "timestamp": row[0],
        "metric_name": metric_name,
        "value": row[1],
        "tags": json.loads(row[2]),
    }


async def list_metrics_summary() -> list[MetricSummary]:
    """List all known metrics with summary statistics."""
    db = await get_db()
    cursor = await db.execute("""
        SELECT
            metric_name,
            COUNT(*) as cnt,
            AVG(value) as avg_val,
            MIN(value) as min_val,
            MAX(value) as max_val,
            MAX(timestamp) as last_ts
        FROM metric_points
        GROUP BY metric_name
        ORDER BY metric_name
    """)
    rows = await cursor.fetchall()

    summaries: list[MetricSummary] = []
    for row in rows:
        name = row[0]
        cnt = row[1]
        avg_val = row[2] or 0.0
        min_val = row[3] or 0.0
        max_val = row[4] or 0.0
        last_ts = row[5] or 0

        # Get stddev separately
        cursor2 = await db.execute(
            "SELECT value FROM metric_points WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 500",
            (name,),
        )
        val_rows = await cursor2.fetchall()
        values = [r[0] for r in val_rows]
        if len(values) > 1:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            stddev = variance ** 0.5
        else:
            stddev = 0.0

        # Get last value
        cursor3 = await db.execute(
            "SELECT value FROM metric_points WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 1",
            (name,),
        )
        last_row = await cursor3.fetchone()
        last_value = last_row[0] if last_row else 0.0

        # Get anomaly count
        cursor4 = await db.execute(
            "SELECT COUNT(*) FROM anomaly_events WHERE metric = ? AND is_anomaly = 1",
            (name,),
        )
        anom_row = await cursor4.fetchone()
        anomaly_count = anom_row[0] if anom_row else 0

        summaries.append(MetricSummary(
            name=name,
            last_value=last_value,
            mean=round(avg_val, 4),
            stddev=round(stddev, 4),
            min_value=min_val,
            max_value=max_val,
            point_count=cnt,
            anomaly_count=anomaly_count,
            last_timestamp=last_ts,
        ))

    return summaries


async def get_recent_window(metric_name: str, count: int = 120) -> list[float]:
    """Get the most recent N values for a metric, ordered oldest to newest."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT value FROM metric_points WHERE metric_name = ? ORDER BY timestamp DESC LIMIT ?",
        (metric_name, count),
    )
    rows = await cursor.fetchall()
    return [row[0] for row in reversed(rows)]
