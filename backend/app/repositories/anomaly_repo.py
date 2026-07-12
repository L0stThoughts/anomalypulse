"""Anomaly events repository."""

from __future__ import annotations

import json
import time
import logging
from typing import Any

from app.database import get_db
from app.models.schemas import AnomalyEventInternal

logger = logging.getLogger("anomalypulse.repo.anomaly")


async def insert_anomaly(event: AnomalyEventInternal) -> None:
    """Persist an anomaly event."""
    db = await get_db()
    await db.execute(
        """INSERT INTO anomaly_events
        (id, metric, timestamp, value, score, detector, severity, is_anomaly, contributing_detectors, context_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.id,
            event.metric,
            event.timestamp,
            event.value,
            event.score,
            event.detector,
            event.severity,
            1 if event.is_anomaly else 0,
            json.dumps(event.contributing_detectors),
            json.dumps(event.context),
            event.created_at or int(time.time() * 1000),
        ),
    )
    await db.commit()


async def get_anomalies(
    metric: str | None = None,
    severity: str | None = None,
    start: int | None = None,
    end: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query anomaly events with optional filters."""
    db = await get_db()
    clauses: list[str] = ["is_anomaly = 1"]
    params: list[Any] = []

    if metric:
        clauses.append("metric = ?")
        params.append(metric)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if start is not None:
        clauses.append("timestamp >= ?")
        params.append(start)
    if end is not None:
        clauses.append("timestamp <= ?")
        params.append(end)

    where = " AND ".join(clauses)
    params.append(limit)

    cursor = await db.execute(
        f"""SELECT id, metric, timestamp, value, score, detector, severity,
                   contributing_detectors, context_json, created_at
            FROM anomaly_events
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT ?""",
        params,
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": row[0],
            "metric": row[1],
            "timestamp": row[2],
            "value": row[3],
            "score": row[4],
            "detector": row[5],
            "severity": row[6],
            "contributing_detectors": json.loads(row[7]),
            "context": json.loads(row[8]),
            "created_at": row[9],
        }
        for row in rows
    ]


async def get_anomaly_count(metric: str) -> int:
    """Get total anomaly count for a metric."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM anomaly_events WHERE metric = ? AND is_anomaly = 1",
        (metric,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0
